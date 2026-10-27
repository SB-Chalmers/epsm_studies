"""Three-state catalogue validation on a stratified national sample from the GIS lake.

Same contract and scoring as ``uddevalla_three_state.py`` (epsm_data
``docs/validation.md``); only the buildings, weather and climate zone differ:

- Buildings come from the epsm_db GIS lake (``service=epsm_lake``, read only).
  Each type × era cohort is ordered by a seeded hash of the building id; the
  first ``--per-cohort`` buildings that pass the screens are kept, and every
  screened-out candidate is recorded with its reason.
- Each municipality gets calendar-year AMYs from smhi2epw at the centroid of
  its registered buildings.
- The catalogue climate zone follows the municipality's county.
- Building type is the lake's own classification (``gis.model_facts``): register
  purposes, complementary buildings excluded, and school/office also from an EPC
  Atemp share of at least 50 %. The Uddevalla label screen is not reapplied.

Steps are resumable and run in order: ``sample``, ``weather``, ``run``,
``summarize`` (``all`` runs them in sequence).

    python validation/catalogue/national_three_state.py all --workers 12
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uddevalla_three_state as shared  # noqa: E402

ROOT = HERE.parents[1]
OUT = Path(os.environ.get("VALIDATION_OUT", ROOT / "output/catalogue_validation/national"))
RESULTS = Path(os.environ.get("VALIDATION_RESULTS", HERE / "results_national"))
SERVICE = os.environ.get("EPSM_LAKE", "service=epsm_lake")
SEED = os.environ.get("VALIDATION_SEED", "catalogue-validation-2026-10-26")
FRAME_DEPTH = 120  # ordered candidates drawn per cohort before screening
AMY_YEARS = range(2014, 2026)
ERA_SQL = """CASE WHEN construction_year <= 1960 THEN 'SE.01' WHEN construction_year <= 1975 THEN 'SE.02'
    WHEN construction_year <= 1985 THEN 'SE.03' WHEN construction_year <= 1995 THEN 'SE.04'
    WHEN construction_year <= 2005 THEN 'SE.05' WHEN construction_year <= 2021 THEN 'SE.06' ELSE 'SE.07' END"""


def read_jsonl(path):
    return shared.read_jsonl(path)


def append_jsonl(path, row):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(row, default=str) + "\n")


def connect():
    import psycopg
    from psycopg.rows import dict_row

    connection = psycopg.connect(SERVICE, row_factory=dict_row)
    connection.execute("SET default_transaction_read_only = on")
    return connection


def frame(depth=FRAME_DEPTH):
    """Ordered candidates per cohort from the lake's single-EPC model export."""
    with connect() as connection:
        return connection.execute(f"""
            SELECT * FROM (
                SELECT building_external_id AS building_id, municipality_code, building_type AS category,
                       construction_year, {ERA_SQL} AS era,
                       row_number() OVER (PARTITION BY building_type, {ERA_SQL}
                                          ORDER BY md5(%(seed)s || building_external_id)) AS rank
                FROM gis.model_export_buildings
                WHERE single_building_epc AND geometry_valid AND construction_year > 0
                  AND building_type IN ('single_family', 'multi_family', 'office', 'school')
                  AND ST_Area(geom) >= %(min_area)s
            ) ordered WHERE rank <= %(depth)s ORDER BY category, era, rank""",
            {"seed": SEED, "min_area": shared.MIN_FOOTPRINT_M2, "depth": depth}).fetchall()


def climate_zone(municipality_code):
    from epsm_data.climate_zones import climate_zone_for_county

    return climate_zone_for_county(municipality_code[:2])


def screen(record, candidate, placeholder_weather):
    """Target, overrides and model facts for one candidate, or an exclusion reason."""
    from epsm.legacy_records import EPSMBuilding, ModelAssemblyError, ModelPolicy
    from epsm_db.epc_heating import heating_target_from_record

    if record.type.value != candidate["category"]:
        return None, f"record type {record.type.value} differs from frame type"
    if not record.single_building_epc:
        return None, "no single-building EPC"
    target = heating_target_from_record(record)
    if target.reported_period_heating_kwh is None:
        return None, "no measured-period heating: " + ", ".join(target.exclusions)
    if any(year not in AMY_YEARS for year in target.years):
        return None, f"measured period outside AMY years {AMY_YEARS.start}-{AMY_YEARS.stop - 1}"
    overrides = {"climate_zone": climate_zone(candidate["municipality_code"])}
    state = None if candidate["era"] == "SE.07" else "existing"
    try:
        building, receipt = EPSMBuilding.from_record(
            record, weather=placeholder_weather, policy=ModelPolicy(),
            overrides={**overrides, **({"renovation_state": state} if state else {})},
            energyplus=shared.ENGINE)  # compile preflight: rejects geometry EnergyPlus cannot take
    except ModelAssemblyError as error:
        return None, f"assembly: {error}"
    heating = building.spec.delivery.heating
    if (heating.carrier if heating else None) != target.carrier:
        return None, "EPC carrier and model carrier differ"
    era = receipt.identities["archetype_assignment"]["era"]
    if era != candidate["era"]:
        return None, f"runner era {era} differs from register era {candidate['era']}"
    return {"target": target, "overrides": overrides}, None


def sample(per_cohort, placeholder_epw, depth=FRAME_DEPTH, exclude=()):
    """Keep the first passing candidates per cohort; resumable by candidate."""
    from epsm_db import Database
    from sweden_ubem.weather import WeatherReference

    db = Database(SERVICE)
    placeholder = WeatherReference.from_epw(placeholder_epw, calendar_year=2023)
    path = OUT / "candidates.jsonl"
    # A kept building the platform cannot simulate (geometry, numerical or warning
    # rejection) is replaced; timeouts are rerun instead. Replacements stay recorded.
    latest_runs = {(r["building_id"], r["state"], r["year"]): r for r in read_jsonl(OUT / "runs.jsonl")}
    failures = {}
    for r in latest_runs.values():
        if r["status"] != "accepted" and "timeout" not in r.get("error", ""):
            failures.setdefault(r["building_id"], r["error"])
    for r in kept_buildings():
        if r["building_id"] in failures:
            append_jsonl(path, {**r, "kept": False, "reason": "simulation: " + failures[r["building_id"]]})
    seen = latest(read_jsonl(path))
    candidates = frame(depth)
    cohorts = {}
    for c in candidates:
        cohorts.setdefault((c["category"], c["era"]), []).append(c)
    for (category, era), group in cohorts.items():
        kept = sum(1 for r in seen.values() if (r["category"], r["era"]) == (category, era) and r["kept"])
        for c in group:
            if kept >= per_cohort:
                break
            key = (category, era, c["building_id"])
            if key in seen or c["building_id"] in exclude:
                continue
            row = {**{k: c[k] for k in ("building_id", "municipality_code", "category", "era", "construction_year", "rank")},
                   "kept": False}
            try:
                record = db.record(c["building_id"])
                result, reason = screen(record, c, placeholder)
            except Exception as error:  # recorded per candidate
                result, reason = None, f"{type(error).__name__}: {error}"
            if result:
                t = result["target"]
                row.update(kept=True, carrier=t.carrier, regime=t.regime,
                           period_start=t.period_start.isoformat(), period_end_exclusive=t.period_end_exclusive.isoformat(),
                           weather_years=list(t.years), measured_kwh=t.reported_period_heating_kwh,
                           epc_atemp_m2=record.atemp_m2, climate_zone=result["overrides"]["climate_zone"],
                           construction_year_source="register")
                kept += 1
            else:
                row["reason"] = reason
            append_jsonl(path, row)
            seen[key] = row
        print(f"{category} {era}: kept {kept} of {sum(1 for k in seen if k[:2] == (category, era))} screened"
              f" ({len(group)} in frame)", flush=True)


def latest(rows):
    """The last row per cohort candidate; later rows supersede earlier screening."""
    return {(r["category"], r["era"], r["building_id"]): r for r in rows}


def kept_buildings():
    return [r for r in latest(read_jsonl(OUT / "candidates.jsonl")).values() if r["kept"]]


def reference_points(codes):
    """Centroid of each municipality's registered buildings, in WGS84."""
    with connect() as connection:
        rows = connection.execute("""
            SELECT municipality_code,
                   ST_Y(ST_Transform(ST_Centroid(ST_Collect(label_point)), 4326)) AS latitude,
                   ST_X(ST_Transform(ST_Centroid(ST_Collect(label_point)), 4326)) AS longitude,
                   count(*) AS buildings
            FROM gis.model_buildings WHERE municipality_code = ANY(%s) AND label_point IS NOT NULL
            GROUP BY municipality_code""", (sorted(codes),)).fetchall()
    return {r["municipality_code"]: r for r in rows}


def build_weather(workers):
    from sweden_ubem.weather import WeatherReference

    buildings = kept_buildings()
    needed = sorted({(b["municipality_code"], y) for b in buildings for y in b["weather_years"]})
    points_path = OUT / "municipality_points.json"
    points = json.loads(points_path.read_text()) if points_path.exists() else {}
    missing = {code for code, _ in needed} - set(points)
    if missing:
        points.update(reference_points(missing))
        points_path.write_text(json.dumps(points, indent=1, default=str))
    path = OUT / "weather.jsonl"
    done = {(r["municipality_code"], r["year"]) for r in read_jsonl(path) if r["status"] == "accepted"}
    tasks = [t for t in needed if t not in done]
    print(f"municipality-years={len(needed)} done={len(done)} pending={len(tasks)}", flush=True)

    def one(code, year):
        p = points[code]
        row = {"municipality_code": code, "year": year, "latitude": p["latitude"], "longitude": p["longitude"],
               "status": "error"}
        try:
            reference = WeatherReference.from_location(latitude=p["latitude"], longitude=p["longitude"],
                                                       year=year, directory=OUT / "weather")
            shutil.rmtree(Path(reference.epw_path).parent / "raw-cache", ignore_errors=True)
            sidecar = json.loads(Path(reference.epw_path + ".json").read_text()) \
                if Path(reference.epw_path + ".json").exists() else {}
            result = sidecar.get("result", {})
            row.update(status="accepted", weather_epw=reference.epw_path, weather_sha256=reference.sha256,
                       station_distance_km=result.get("coordinate_distance_km"),
                       interpolated_fraction=result.get("interpolated_fraction"))
        except Exception as error:  # recorded per municipality-year
            row["error"] = f"{type(error).__name__}: {error}"
        return row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, future in enumerate(as_completed([pool.submit(one, *t) for t in tasks]), 1):
            row = future.result()
            append_jsonl(path, row)
            print(f"weather {i}/{len(tasks)} {row['municipality_code']} {row['year']} {row['status']} "
                  f"{row.get('error', '')}", flush=True)


def weather_items():
    return {(r["municipality_code"], r["year"]): (r["weather_epw"], r["weather_sha256"])
            for r in read_jsonl(OUT / "weather.jsonl") if r["status"] == "accepted"}


def run(workers, timeout=600):
    from epsm_db import Database
    from epsm_db.epc_heating import heating_target_from_record

    db = Database(SERVICE)
    weather = weather_items()
    runs_path = OUT / "runs.jsonl"
    done = {(r["building_id"], r["state"], r["year"]) for r in read_jsonl(runs_path) if r["status"] == "accepted"}
    tasks = []
    for b in kept_buildings():
        states = shared.states_for(b["era"])
        if all((b["building_id"], s, y) in done for s in states for y in b["weather_years"]):
            continue
        record = db.record(b["building_id"])
        target = heating_target_from_record(record)
        if target.reported_period_heating_kwh != b["measured_kwh"]:
            raise ValueError(f"Heating target changed since sampling: {b['building_id']}")
        overrides = {"climate_zone": b["climate_zone"]}
        for s in states:
            for y in b["weather_years"]:
                if (b["building_id"], s, y) in done:
                    continue
                item = weather.get((b["municipality_code"], y))
                if item is None:
                    append_jsonl(runs_path, {"building_id": b["building_id"], "state": s, "year": y,
                                             "status": "error", "error": "no accepted AMY for municipality-year"})
                    continue
                tasks.append((record, target, overrides, s, y, item))
    print(f"pending_runs={len(tasks)} resumed={len(done)}", flush=True)
    # Processes, not threads: each run spends seconds in Python around EnergyPlus.
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(shared.run_one, *t, out=OUT, prune=True, timeout=timeout) for t in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            row = future.result()
            append_jsonl(runs_path, row)
            print(f"{i}/{len(tasks)} {row['state']} {row['year']} {row['building_id']} {row['status']} "
                  f"{row.get('error', '')}", flush=True)


REASON_CLASSES = (
    ("Kiva", "Kiva ground floor with holes or disconnected parts"),
    ("Near-coincident", "near-coincident footprint vertices"),
    ("Pitched roof on touching", "pitched roof over touching parts"),
    ("adjacency", "nonreciprocal surface adjacency"),
    ("CheckWarmupConvergence", "EnergyPlus warm-up non-convergence"),
    ("Very small surface area", "sliver window or surface"),
    ("FixViewFactors", "incomplete view factors (attic geometry)"),
    ("WetBulb", "EnergyPlus psychrometric non-convergence"),
    ("not_measurement_indicated", "no measured twelve-month period (calculated EPC)"),
    ("measurement_period_not_twelve_months", "no measured twelve-month period (calculated EPC)"),
    ("mixed_or_missing_carrier", "mixed or missing EPC heating carrier"),
    ("temporal conflict", "EPC dated before construction"),
    ("full-floor geometry", "heights do not form whole storeys"),
    ("geometry-mismatched height", "missing or unresolved height evidence"),
    ("AMY years", "measured period outside the AMY years"),
    ("carrier differ", "EPC and model heating carrier differ"),
    ("Simulation acceptance rejected", "EnergyPlus run rejected by acceptance policy"),
    ("assembly:", "other footprint or basement assembly failure"),
)


def reason_class(reason):
    return next((label for key, label in REASON_CLASSES if key in reason), reason.split(":")[0])


def code_identity(module):
    """Commit and uncommitted-diff hash of the checkout a module was imported from."""
    root = Path(__import__(module).__file__).resolve().parents[2]
    diff = shared.git(root, "diff", "HEAD")
    return {"path": str(root), "commit": shared.git(root, "rev-parse", "HEAD"),
            "branch": shared.git(root, "branch", "--show-current"),
            "diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None}


def summarize():
    from sweden_ubem.records import implementation_hash

    candidates = list(latest(read_jsonl(OUT / "candidates.jsonl")).values())
    metas = [{**b, "measured_kwh": b["measured_kwh"]} for b in candidates if b["kept"]]
    excluded = [{**{k: c[k] for k in ("building_id", "category", "era", "municipality_code")},
                 "stage": "simulation" if c["reason"].startswith("simulation:") else "screen",
                 "reason": reason_class(c["reason"]), "detail": c["reason"].removeprefix("simulation: ")}
                for c in candidates if not c["kept"]]
    summary = shared.summarize(metas, read_jsonl(OUT / "runs.jsonl"), excluded)
    # Buildings that failed in this run (rather than being replaced) carry raw errors.
    for row in summary["excluded"]:
        if "detail" not in row:
            row["detail"], row["reason"] = row["reason"], reason_class(row["reason"])
    summary["exclusion_counts"] = dict(Counter(f"{e['stage']}: {e['reason']}" for e in summary["excluded"]))
    weather = read_jsonl(OUT / "weather.jsonl")
    manifest = {
        "contract": "epsm_data docs/validation.md",
        "source": SERVICE.replace("service=", "PostgreSQL service "), "seed": SEED,
        "deepest_rank_screened": {f"{c} {e}": max(r["rank"] for r in candidates if (r["category"], r["era"]) == (c, e))
                                  for c, e in sorted({(r["category"], r["era"]) for r in candidates})},
        "candidates_screened": len(candidates),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "implementation_sha256": {n: implementation_hash(n) for n in ("epsm", "epsm_db", "epsm_core", "epsm_data")},
        "code": {n: code_identity(n) for n in ("epsm", "epsm_db", "epsm_core", "epsm_data", "smhi2epw")},
        "weather": f"smhi2epw calendar AMYs at municipality building centroids; {sum(r['status'] == 'accepted' for r in weather)} accepted municipality-years",
        "climate_zone": "epsm_data.climate_zones.climate_zone_for_county(municipality code[:2])",
        "states": list(shared.STATES), "match_tolerance": shared.MATCH_TOLERANCE, "minimum_cohort": shared.MIN_COHORT,
        "no_calibration": True,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps({"manifest": manifest, **summary}, indent=2, default=str) + "\n")
    (RESULTS / "tables.md").write_text(shared.markdown_tables(summary))
    for name in ("buildings", "excluded"):
        rows = summary[name]
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with (RESULTS / f"{name}.csv").open("w", newline="") as stream:
            import csv

            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary["overall"], indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=("sample", "weather", "run", "summarize", "all"))
    parser.add_argument("--per-cohort", type=int, default=20)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--exclude-sample", type=Path,
                        help="candidates.jsonl of another sample whose kept buildings are skipped")
    parser.add_argument("--frame-depth", type=int, default=FRAME_DEPTH,
                        help="Ordered candidates drawn per cohort; deepening keeps earlier screening")
    parser.add_argument("--weather-workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600, help="EnergyPlus wall-clock seconds per run")
    parser.add_argument("--placeholder-epw", default=os.environ.get("PLACEHOLDER_EPW"),
                        help="Any EPW; used only to assemble models while screening")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.step in ("sample", "all"):
        if not args.placeholder_epw:
            raise ValueError("Supply --placeholder-epw for screening")
        exclude = ({r["building_id"] for r in latest(read_jsonl(args.exclude_sample)).values() if r["kept"]}
                   if args.exclude_sample else set())
        sample(args.per_cohort, args.placeholder_epw, args.frame_depth, exclude)
    if args.step in ("weather", "all"):
        build_weather(args.weather_workers)
    if args.step in ("run", "all"):
        run(args.workers, args.timeout)
    if args.step in ("summarize", "all"):
        summarize()


if __name__ == "__main__":
    main()
