"""Three-state catalogue validation on the screened Uddevalla EPC panel.

Implements the contract in epsm_data ``docs/validation.md``: each building is
simulated with the Existing, Standard and Advanced catalogue states (SE.07: one
state) through the platform record runner, and its measured EPC heating is
compared with each result. Nothing is tuned per building.

Reused from epsm_db (read only): the screened panel and source assignments, the
EPC matching in the database, the reported-period heating target and the
checksum-checked calendar AMY files. Simulations are new and run against the
installed catalogue. Accepted building/state/year runs are resumed.

    UBEM_DATABASE_URL=... python validation/catalogue/uddevalla_three_state.py
    python validation/catalogue/uddevalla_three_state.py --summarize-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import date
from pathlib import Path

EPSM_DB = Path(os.environ.get("EPSM_DB_ROOT", Path.home() / "GitHub/epsm_db"))
STUDY = EPSM_DB / "output/analysis/uddevalla-consistency-2026-10-13"
PANEL = STUDY / "baseline_policy_v3_panel/results.jsonl"
ASSIGNMENTS = STUDY / "archetype_stock/building_assignments.csv"
AMY_RUNS = STUDY / "amy_period_comparison/runs.jsonl"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = Path(os.environ.get("VALIDATION_OUT", ROOT / "output/catalogue_validation/uddevalla"))
RESULTS = HERE / "results"
ENGINE = os.environ.get("ENERGYPLUS", "/Applications/OpenStudio-3.9.0/EnergyPlus/energyplus")
STATES = ("existing", "standard", "advanced")
CATEGORIES = ("single_family", "multi_family", "office", "school")
ERAS = ("SE.01", "SE.02", "SE.03", "SE.04", "SE.05", "SE.06", "SE.07")
MIN_FOOTPRINT_M2 = 100.0
MATCH_TOLERANCE = 0.20
MIN_COHORT = 10
REPOS = ("epsm_data", "epsm_core", "epsm", "epsm_db", "epsm_lca", "smhi2epw")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()] if Path(path).exists() else []


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligible(category, labels):
    """Source-function screen from epsm_db scripts/compare_uddevalla_epc_amy.py."""
    if any(label.startswith("Komplementbyggnad;") for label in labels):
        return False
    return {
        "single_family": bool(set(labels) & {"Bostad;Småhus friliggande", "Bostad;Småhus kedjehus", "Bostad;Småhus radhus"}),
        "multi_family": "Bostad;Flerfamiljshus" in labels,
        "school": bool(set(labels) & {"Samhallsfunktion;Skola", "Samhällsfunktion;Skola"}),
        "office": any(label.startswith("Verksamhet;") for label in labels),
    }.get(category, False)


def panel():
    """Screened panel plus excluded panel buildings with their reasons."""
    with ASSIGNMENTS.open(newline="") as stream:
        sources = {row["building_id"]: row for row in csv.DictReader(stream)}
    selected, excluded = [], []
    for old in read_jsonl(PANEL):
        if not old.get("success"):
            excluded.append({"building_id": old["building_id"], "category": old.get("category"), "era": old.get("era"),
                             "stage": "panel", "reason": "earlier baseline assembly failed"})
            continue
        source = sources[old["building_id"]]
        reason = (source["exclusion_reason"] or
                  (None if eligible(old["category"], json.loads(source["source_use_labels"])) else "source function not eligible") or
                  (None if (old.get("footprint_m2") or 0) >= MIN_FOOTPRINT_M2 else f"footprint below {MIN_FOOTPRINT_M2:.0f} m²"))
        if reason:
            excluded.append({"building_id": old["building_id"], "category": old["category"], "era": old["era"],
                             "stage": "screen", "reason": reason})
        else:
            selected.append((old, source))
    return selected, excluded


def amy_weather():
    """Calendar-year AMYs already compiled by epsm_db, keyed by year."""
    weather = {}
    for row in read_jsonl(AMY_RUNS):
        if row["status"] == "accepted":
            item = weather.setdefault(row["year"], (row["weather_epw"], row["weather_sha256"]))
            if item != (row["weather_epw"], row["weather_sha256"]):
                raise ValueError(f"Inconsistent AMY for {row['year']}")
    return weather


def repo_identity(name):
    path = Path.home() / "GitHub" / name
    git = lambda *a: subprocess.run(["git", "-C", str(path), *a], capture_output=True, text=True).stdout.strip()
    diff = git("diff", "HEAD")
    return {"commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "dirty_files": len(git("status", "--porcelain").splitlines()),
            "diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None}


def prepare(old, source):
    """Fetch the record, EPC target and assembly overrides for one building."""
    from sweden_ubem.enums import BuildingType
    from sweden_ubem.epc_heating import heating_target_from_record
    from sweden_ubem.io import fetch_record

    record = fetch_record.from_uuid(old["building_id"], dataset="uddevalla")
    if record.selected_certificate is None or record.selected_certificate["certificate_id"] != old["certificate_id"]:
        raise ValueError("Selected EPC changed relative to the panel snapshot")
    if record.geometry.area < MIN_FOOTPRINT_M2:
        raise ValueError("Footprint no longer passes minimum area")
    if record.type.value != old["category"]:
        record = replace(record, type=BuildingType(old["category"]))
    target = heating_target_from_record(record)
    overrides = {}
    # Same rule as the earlier Uddevalla runs: when the register year falls in a
    # different era from the EPC-reported construction year, use the EPC year.
    if source["adapter_era"] != source["epc_era"]:
        overrides["construction_year"] = int(source["epc_year"])
    return record, target, overrides


def allow_single_state_era():
    """Let the record runner assemble SE.07, whose catalogue slot has no state.

    ``EPSMBuilding.from_record`` always passes ``default_state="existing"``,
    which the resolver rejects for SE.07. Until the runner handles this, map that
    default to the single configuration; every other era is unchanged.
    """
    import epsm.catalogue_application as application
    from epsm_data.classification import era_for_year

    resolve = application.resolve_building_archetype
    if getattr(resolve, "single_state_era_shim", False):
        return

    def resolve_with_single_state(*, construction_year, default_state=None, **kwargs):
        if default_state == "existing" and era_for_year(int(construction_year)) == "SE.07":
            default_state = None
        return resolve(construction_year=construction_year, default_state=default_state, **kwargs)

    resolve_with_single_state.single_state_era_shim = True
    application.resolve_building_archetype = resolve_with_single_state


def run_one(record, target, overrides, state, year, weather_item):
    from epsm.legacy_records import EPSMBuilding, ModelPolicy
    from sweden_ubem.epc_heating import period_heating_kwh
    from sweden_ubem.weather import WeatherReference

    allow_single_state_era()
    bid = record.building_id
    row = {"building_id": bid, "state": state, "year": year, "status": "error"}
    try:
        epw, digest = weather_item
        weather = WeatherReference.from_epw(epw, calendar_year=year)
        if weather.sha256 != digest:
            raise ValueError("AMY checksum changed")
        row["weather_sha256"] = digest
        building, receipt = EPSMBuilding.from_record(
            record, weather=weather, policy=ModelPolicy(),
            overrides={**overrides, **({"renovation_state": state} if state else {})}, energyplus=ENGINE,
        )
        heating = building.spec.delivery.heating
        row["model_carrier"] = heating.carrier if heating else None
        if row["model_carrier"] != target.carrier:
            raise ValueError("EPC carrier and model carrier differ")
        assignment = receipt.identities["archetype_assignment"]
        row.update(archetype_id=assignment["archetype_id"], era=assignment["era"],
                   ventilation=receipt.fields["ventilation"]["model_value"],
                   ventilation_basis=receipt.fields["ventilation"]["model_state"],
                   wwr=receipt.fields["wwr"]["model_value"],
                   atemp_m2=building.spec.load_reference_area_m2,
                   conditioned_area_m2=building.spec.geometry.conditioned_floor_area_m2,
                   quality=receipt.quality)
        directory = OUT / "simulation" / (state or "single") / bid / str(year)
        directory.mkdir(parents=True, exist_ok=True)
        result = building.simulate(directory, energyplus=ENGINE, timeout_seconds=600)
        if not result.diagnostics["accepted"]:
            raise ValueError("EPSM Core rejected simulation")
        row["annual_heating_kwh"] = result.scalars["space_heating_carrier_input_kwh"]
        row["period_piece_heating_kwh"] = period_heating_kwh(
            result.hourly["space_heating_carrier_input_kwh"], year, target.period_start, target.period_end_exclusive)
        row["status"] = "accepted"
    except Exception as error:  # recorded per run; one failure must not stop the panel
        row["error"] = f"{type(error).__name__}: {error}"
    return row


def states_for(era):
    return (None,) if era == "SE.07" else STATES


def classify(r):
    """Covered/matched per docs/validation.md for one building's ratios."""
    if "single" in r:
        lo = hi = r["single"]
        matched = {"single": r["single"]} if abs(r["single"] - 1) <= MATCH_TOLERANCE else {}
    else:
        lo, hi = sorted((r["advanced"], r["existing"]))
        matched = {s: r[s] for s in STATES if abs(r[s] - 1) <= MATCH_TOLERANCE}
    covered = lo <= 1 <= hi
    selected = min(matched, key=lambda s: abs(matched[s] - 1)) if matched else None
    # Where the measured value lies relative to the simulated range.
    position = "inside" if covered else ("below_range" if lo > 1 else "above_range")
    return covered, selected, position


def summarize(buildings_meta, runs, excluded):
    accepted = {(r["building_id"], r["state"], r["year"]): r for r in runs if r["status"] == "accepted"}
    errors = {}
    for r in runs:
        if r["status"] != "accepted" and (r["building_id"], r["state"], r["year"]) not in accepted:
            errors.setdefault(r["building_id"], r["error"])
    buildings, excluded = [], list(excluded)
    for meta in buildings_meta:
        bid = meta["building_id"]
        if "exclusion" in meta:
            excluded.append(meta)
            continue
        era = meta["era"]
        keys = [(bid, s, y) for s in states_for(era) for y in meta["weather_years"]]
        if any(k not in accepted for k in keys):
            excluded.append({**{k: meta[k] for k in ("building_id", "category", "era")}, "stage": "simulation",
                             "reason": errors.get(bid, "simulation incomplete")})
            continue
        observed = meta["measured_kwh"]
        row = {**meta}
        ratios = {}
        for s in states_for(era):
            modelled = sum(accepted[bid, s, y]["period_piece_heating_kwh"] for y in meta["weather_years"])
            ratios[s or "single"] = modelled / observed
            row[f"{s or 'single'}_kwh"] = modelled
            row[f"{s or 'single'}_r"] = modelled / observed
        covered, selected, position = classify(ratios)
        first = accepted[keys[0]]
        row.update(covered=covered, matched=selected is not None, selected_state=selected or "none",
                   position=position, ventilation=first["ventilation"], ventilation_basis=first["ventilation_basis"],
                   atemp_m2=first["atemp_m2"], conditioned_area_m2=first["conditioned_area_m2"],
                   atemp_to_geometry=first["atemp_m2"] / first["conditioned_area_m2"],
                   standard_above_existing="standard" in ratios and ratios["standard"] > ratios["existing"],
                   quality="; ".join(first["quality"]))
        buildings.append(row)

    def stats(group):
        n = len(group)
        if not n:
            return {"n": 0}
        existing = [b.get("existing_r", b.get("single_r")) for b in group]
        return {"n": n, "small_cohort": n < MIN_COHORT,
                "coverage_rate": sum(b["covered"] for b in group) / n,
                "match_rate": sum(b["matched"] for b in group) / n,
                "existing_median_r": statistics.median(existing),
                "advanced_median_r": statistics.median(adv) if (adv := [b["advanced_r"] for b in group if "advanced_r" in b]) else None,
                "selected": dict(Counter(b["selected_state"] for b in group)),
                "position": dict(Counter(b["position"] for b in group))}

    cohorts = [{"category": c, "era": e, **stats([b for b in buildings if b["category"] == c and b["era"] == e])}
               for c in CATEGORIES for e in ERAS]
    by_type = [{"category": c, **stats([b for b in buildings if b["category"] == c])} for c in CATEGORIES]
    by_carrier = [{"carrier": c, **stats([b for b in buildings if b["carrier"] == c])}
                  for c in sorted({b["carrier"] for b in buildings})]
    return {"overall": stats(buildings), "cohorts": [c for c in cohorts if c["n"]], "by_type": by_type,
            "by_carrier": by_carrier, "buildings": buildings, "excluded": excluded,
            "exclusion_counts": dict(Counter(f"{e['stage']}: {e['reason']}" for e in excluded))}


def markdown_tables(summary):
    """Cohort, type, carrier and exclusion tables for the report."""
    pct = lambda x: f"{100 * x:.0f}%"
    sel = lambda c: " / ".join(str(c["selected"].get(s, 0)) for s in (*STATES, "single", "none"))
    pos = lambda c: " / ".join(str(c["position"].get(p, 0)) for p in ("below_range", "inside", "above_range"))
    head = ("| {} | n | Coverage | Match | Existing median r | Advanced median r | Selected E / S / A / SE.07 / none "
            "| Measured below / inside / above range |\n|---|---:|---:|---:|---:|---:|---:|---:|\n")
    row = lambda label, c: (f"| {label} | {c['n']}{'*' if c['small_cohort'] else ''} | {pct(c['coverage_rate'])} | "
                            f"{pct(c['match_rate'])} | {c['existing_median_r']:.2f} | "
                            f"{'—' if c['advanced_median_r'] is None else format(c['advanced_median_r'], '.2f')} | {sel(c)} | {pos(c)} |\n")
    out = ["## Cohorts (type × era)\n\n", head.format("Cohort")]
    out += [row(f"{c['category']} {c['era']}", c) for c in summary["cohorts"]]
    out += ["\n## By type\n\n", head.format("Type")]
    out += [row(c["category"], c) for c in summary["by_type"] if c["n"]]
    out += ["\n## By heating carrier\n\n", head.format("Carrier")]
    out += [row(c["carrier"], c) for c in summary["by_carrier"]]
    out += ["\n## Overall\n\n", head.format("Panel"), row("all", summary["overall"])]
    out += ["\n\\* n < 10: reported, not a cohort result.\n\n## Exclusions\n\n| Stage: reason | Buildings |\n|---|---:|\n"]
    out += [f"| {k} | {v} |\n" for k, v in sorted(summary["exclusion_counts"].items(), key=lambda kv: -kv[1])]
    return "".join(out)


def write_outputs(summary, manifest):
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "tables.md").write_text(markdown_tables(summary))
    (RESULTS / "summary.json").write_text(json.dumps({"manifest": manifest, **summary}, indent=2, default=str) + "\n")
    for name in ("buildings", "excluded"):
        rows = summary[name]
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with (RESULTS / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    from sweden_ubem.records import implementation_hash

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "contract": "epsm_data docs/validation.md",
        "panel_sha256": sha256(PANEL), "assignments_sha256": sha256(ASSIGNMENTS), "amy_runs_sha256": sha256(AMY_RUNS),
        "script_sha256": sha256(__file__),
        "implementation_sha256": {n: implementation_hash(n) for n in ("epsm", "sweden_ubem", "epsm_core", "epsm_data")},
        "repositories": {n: repo_identity(n) for n in REPOS},
        "states": list(STATES), "match_tolerance": MATCH_TOLERANCE, "minimum_cohort": MIN_COHORT,
        "target": "EPC reported delivered space-heating carrier input over the exact measured twelve months",
        "model": "epsm.legacy_records.EPSMBuilding.from_record, ModelPolicy() defaults, renovation_state override only",
        "se07_shim": "SE.07 'existing' default mapped to the single catalogue configuration (allow_single_state_era)",
        "no_calibration": True,
    }
    meta_path, runs_path = OUT / "buildings.jsonl", OUT / "runs.jsonl"
    selected, excluded = panel()
    weather = amy_weather()
    if args.summarize_only:
        metas = read_jsonl(meta_path)
    else:
        if not os.environ.get("UBEM_DATABASE_URL"):
            raise ValueError("Set a read-only UBEM_DATABASE_URL")
        metas, tasks = [], []
        for old, source in selected:
            bid = old["building_id"]
            base = {"building_id": bid, "category": old["category"], "era": old["era"],
                    "certificate_id": old["certificate_id"]}
            try:
                record, target, overrides = prepare(old, source)
            except Exception as error:
                metas.append({**base, "stage": "record", "reason": f"{type(error).__name__}: {error}", "exclusion": True})
                continue
            if target.reported_period_heating_kwh is None:
                metas.append({**base, "stage": "target", "exclusion": True,
                              "reason": "no measured-period heating: " + ", ".join(target.exclusions)})
                continue
            missing = [y for y in target.years if y not in weather]
            if missing:
                metas.append({**base, "stage": "weather", "exclusion": True, "reason": f"no AMY for {missing}"})
                continue
            from epsm_data.classification import era_for_year

            # Same year precedence as the record runner: override, register, EPC.
            year = (overrides.get("construction_year") or record.facts.get("construction_year")
                    or record.observation("EgenNybyggAr", integer=True)[0])
            era = era_for_year(int(year))
            metas.append({**base, "era": era, "construction_year": int(year),
                          "construction_year_source": "epc_override" if overrides else "register",
                          "carrier": target.carrier, "regime": target.regime,
                          "period_start": target.period_start.isoformat(),
                          "period_end_exclusive": target.period_end_exclusive.isoformat(),
                          "weather_years": list(target.years), "measured_kwh": target.reported_period_heating_kwh,
                          "epc_atemp_m2": record.atemp_m2})
            tasks.extend((record, target, overrides, s, y, weather[y]) for s in states_for(era) for y in target.years)
        meta_path.write_text("".join(json.dumps(m, default=str) + "\n" for m in metas))
        done = {(r["building_id"], r["state"], r["year"]) for r in read_jsonl(runs_path) if r["status"] == "accepted"}
        tasks = [t for t in tasks if (t[0].building_id, t[3], t[4]) not in done]
        print(f"buildings={len(metas)} resumed={len(done)} pending_runs={len(tasks)}", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool, runs_path.open("a") as stream:
            futures = [pool.submit(run_one, *t) for t in tasks]
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                stream.write(json.dumps(result, default=str) + "\n")
                stream.flush()
                print(f"{i}/{len(tasks)} {result['state']} {result['year']} {result['building_id']} "
                      f"{result['status']} {result.get('error', '')}", flush=True)
    summary = summarize(metas, read_jsonl(runs_path), excluded)
    write_outputs(summary, manifest)
    print(json.dumps(summary["overall"], indent=2), flush=True)


if __name__ == "__main__":
    main()
