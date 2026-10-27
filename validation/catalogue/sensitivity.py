"""Stage 3 of ``calibration_plan.md``: one-at-a-time sensitivity runs, then a type-level fit.

Each named run moves one shortlisted parameter to the end of its evidence range for
the building types it applies to, on the same buildings, states, years and AMYs as
the version-4 baseline in ``VALIDATION_OUT``. Runs where the parameter touches nothing
are recorded as ``not_applicable`` and keep the baseline value.

    python validation/catalogue/sensitivity.py run --workers 13
    python validation/catalogue/sensitivity.py fit
    python validation/catalogue/sensitivity.py run --only fitted --params results_sensitivity/fitted_params.json
    python validation/catalogue/sensitivity.py compare   # fitted bundle per type against the rules
    python validation/catalogue/sensitivity.py decided   # the accepted changes only

Set ``VALIDATION_OUT`` to the hold-out output to run ``fitted``, ``compare`` and
``decided`` on the hold-out sample.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ.setdefault("VALIDATION_OUT", str(ROOT / "output/catalogue_validation/national_templates"))
sys.path.insert(0, str(HERE))
import national_three_state as national  # noqa: E402
import perturbations  # noqa: E402
import uddevalla_three_state as shared  # noqa: E402

RESULTS = Path(os.environ.get("SENSITIVITY_RESULTS", HERE / "results_sensitivity"))
SENSITIVITY_OUT = Path(os.environ.get("SENSITIVITY_OUT", national.OUT.parent / f"sensitivity_{national.OUT.name}"))
HOUSING = ("single_family", "multi_family")
ALL_TYPES = HOUSING + ("office", "school")
ALL_STATES = ("existing", "standard", "advanced", None)
BOUNDS = ("existing", "advanced", None)  # the states the stage-1 tolerances test

# name -> (params, building types, states). Values are the far end of each range in
# the plan's shortlist; the baseline is the other end.
RUNS = {
    # #1 BETSI measured indoor temperature: multifamily 22.2–23.0 °C by era, single-family 20.8–21.9.
    "setpoint_housing": ({"setpoint_c": {"multi_family": 23.0, "single_family": 21.9}}, HOUSING, ALL_STATES),
    # #2 BETSI tracer gas, self-draught total air change: single-family 0.40, multifamily 0.39 ACH.
    "self_draught": ({"self_draught_total_ach": {"single_family": 0.40, "multi_family": 0.39}}, HOUSING, ALL_STATES),
    # #6 Sveby offices: owners report 1.2–1.6 L/(s·m²) (model 1.3) and 06–20 operation (model 07–19).
    "office_flow": ({"vent_flow_factor": {"office": 1.6 / 1.3}}, ("office",), ALL_STATES),
    "office_hours": ({"vent_extra_hours": {"office": 1}}, ("office",), ALL_STATES),
    # #3 and #4 are weakly sourced: diagnostic responses only, bound states only.
    "infiltration_new": ({"infiltration_factor": dict.fromkeys(ALL_TYPES, 3.0)}, ALL_TYPES, ("existing", None)),
    "ftx_recovery": ({"ftx_recovery_delta": dict.fromkeys(ALL_TYPES, -0.2)}, ALL_TYPES, BOUNDS),
}


def runs_path(name):
    return SENSITIVITY_OUT / name / "runs.jsonl"


def run(names, workers, timeout, extra_params=None):
    from epsm_db import Database
    from epsm_db.epc_heating import heating_target_from_record

    db = Database(national.SERVICE)
    weather = national.weather_items()
    baseline = {(r["building_id"], r["state"], r["year"]) for r in national.read_jsonl(national.OUT / "runs.jsonl")
                if r["status"] == "accepted"}
    tasks = []
    records = {}
    for name in names:
        params, types, states = (extra_params, ALL_TYPES, ALL_STATES) if name == "fitted" else RUNS[name]
        (SENSITIVITY_OUT / name).mkdir(parents=True, exist_ok=True)
        (SENSITIVITY_OUT / name / "params.json").write_text(json.dumps(params, indent=1) + "\n")
        done = {(r["building_id"], r["state"], r["year"]) for r in national.read_jsonl(runs_path(name))
                if r["status"] in ("accepted", "not_applicable")}
        transform = functools.partial(perturbations.apply, params=params)
        for b in national.kept_buildings():
            if b["category"] not in types:
                continue
            for s in shared.states_for(b["era"]):
                if s not in states:
                    continue
                for y in b["weather_years"]:
                    key = (b["building_id"], s, y)
                    if key in done or key not in baseline:
                        continue
                    if b["building_id"] not in records:
                        record = db.record(b["building_id"])
                        target = heating_target_from_record(record)
                        if target.reported_period_heating_kwh != b["measured_kwh"]:
                            raise ValueError(f"Heating target changed since sampling: {b['building_id']}")
                        records[b["building_id"]] = (record, target)
                    record, target = records[b["building_id"]]
                    item = weather[(b["municipality_code"], y)]
                    tasks.append((name, (record, target, {"climate_zone": b["climate_zone"]}, s, y, item), transform))
    print(f"pending_runs={len(tasks)}", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(shared.run_one, *args, out=SENSITIVITY_OUT / name, prune=True, timeout=timeout,
                               transform=transform): name for name, args, transform in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            name, row = futures[future], future.result()
            national.append_jsonl(runs_path(name), row)
            print(f"{i}/{len(tasks)} {name} {row['state']} {row['year']} {row['building_id']} {row['status']} "
                  f"{row.get('error', '')}", flush=True)


# Fitted parameters per type: (run name, value at t=0 (baseline), value at t=1, allowed t range).
# Ranges are the plan's evidence ranges expressed as a fraction of the baseline-to-end step.
FIT = {
    "single_family": {
        "setpoint_housing": (21.0, 21.9, (20.8 - 21.0) / 0.9, 1.0),  # BETSI 20.8–21.9 °C
        "self_draught": (None, 0.40, 0.0, 1.0),  # template 0.5 ACH + infiltration -> BETSI 0.40 total
    },
    "multi_family": {
        "setpoint_housing": (21.0, 23.0, 0.6, 1.0),  # BETSI 22.2–23.0 °C
        "self_draught": (None, 0.39, 0.0, 1.0),
    },
    "office": {
        "office_flow": (1.3, 1.6, (1.2 - 1.3) / 0.3, 1.0),  # owners 1.2–1.6 L/(s·m²); model 1.3
        "office_hours": (0, 1, 0.0, 1.0),  # 07–19 or 06–20; whole hours only
    },
    "school": {},
}
DIAGNOSTIC = ("infiltration_new", "ftx_recovery")
# #8 is a refinement to the field average, not a fit: COP 3.0 -> 2.75 (Swedish SPF 2.6–2.9).
HEAT_PUMP_COP = 2.75
POLICY_COP = 3.0
GRID = 20
TOLERANCE = 0.15
MATCH_TARGET = 0.50


def load(out):
    """Per-building modelled kWh by (state, year) from a runs file; latest row wins."""
    rows = {}
    for r in national.read_jsonl(out):
        rows[r["building_id"], r["state"], r["year"]] = r
    return rows


def buildings():
    """Kept buildings with a complete baseline, as in the national summary."""
    base = load(national.OUT / "runs.jsonl")
    kept = []
    for b in national.kept_buildings():
        keys = [(b["building_id"], s, y) for s in shared.states_for(b["era"]) for y in b["weather_years"]]
        if all(base.get(k, {}).get("status") == "accepted" for k in keys):
            kept.append(b)
    return kept, base


def modelled(b, rows, base, state):
    """Period kWh for one state: perturbed where run, baseline where not applicable."""
    total = 0.0
    for y in b["weather_years"]:
        key = (b["building_id"], state, y)
        r = rows.get(key) if rows is not None else None
        if r is None or r["status"] != "accepted":
            if r is not None and r["status"] not in ("not_applicable",):
                return None
            r = base[key]
        total += r["period_piece_heating_kwh"]
    return total


def responses(names, drop_incomplete=False):
    """{building_id: {"base": {state: kWh}, name: {state: delta kWh}}} for each named run.

    A failed perturbed run keeps the baseline value and is counted, or with
    ``drop_incomplete`` removes the building from the comparison."""
    kept, base = buildings()
    loaded = {name: load(runs_path(name)) for name in names}
    table, missing = {}, {name: 0 for name in names}
    for b in kept:
        states = [s or "single" for s in shared.states_for(b["era"])]
        entry = {"meta": b, "base": {}}
        for s in shared.states_for(b["era"]):
            entry["base"][s or "single"] = modelled(b, None, base, s)
        for name in names:
            _, types, run_states = RUNS.get(name, (None, ALL_TYPES, ALL_STATES))
            delta = {}
            for s in shared.states_for(b["era"]):
                if b["category"] not in types or s not in run_states:
                    delta[s or "single"] = 0.0
                    continue
                value = modelled(b, loaded[name], base, s)
                if value is None:
                    missing[name] += 1
                    if drop_incomplete:
                        entry = None
                        break
                    value = entry["base"][s or "single"]
                delta[s or "single"] = value - entry["base"][s or "single"]
            if entry is None:
                break
            entry[name] = delta
        if entry is None:
            continue
        assert set(entry["base"]) == set(states)
        table[b["building_id"]] = entry
    return table, missing


def ratios(entry, weights, cop=POLICY_COP):
    """State ratios at fractions ``weights`` {run: t} of each step; COP rescales heat-pump input."""
    if isinstance(cop, dict):
        cop = cop.get(entry["meta"]["category"], POLICY_COP)
    scale = POLICY_COP / cop if entry["meta"]["carrier"] == "heat_pump" else 1.0
    measured = entry["meta"]["measured_kwh"]
    return {s: scale * (entry["base"][s] + sum(t * entry[name][s] for name, t in weights.items())) / measured
            for s in entry["base"]}


def score(entries, weights_by_type, cop=POLICY_COP):
    """Per-cohort above / below / match shares and the stage-1 penalty."""
    cohorts = {}
    for e in entries:
        m = e["meta"]
        r = ratios(e, weights_by_type.get(m["category"], {}), cop)
        covered, selected, position = shared.classify(r)
        c = cohorts.setdefault((m["category"], m["era"]), {"n": 0, "above": 0, "below": 0, "match": 0, "single": "single" in r})
        c["n"] += 1
        c["above"] += position == "above_range"
        c["below"] += position == "below_range" and "single" not in r
        c["match"] += selected is not None
    for c in cohorts.values():
        for k in ("above", "below", "match"):
            c[k] /= c["n"]
        c["penalty"] = (max(0, c["above"] - TOLERANCE) + (0 if c["single"] else max(0, c["below"] - TOLERANCE))
                        + max(0, MATCH_TARGET - c["match"]))
        c["meets"] = c["penalty"] == 0
    return cohorts


def overall(cohorts, category=None):
    chosen = [c for (cat, _), c in cohorts.items() if category in (None, cat)]
    n = sum(c["n"] for c in chosen)
    ranged = [c for c in chosen if not c["single"]]
    nr = sum(c["n"] for c in ranged)
    return {"n": n, "above": sum(c["above"] * c["n"] for c in chosen) / n,
            "below": sum(c["below"] * c["n"] for c in ranged) / nr if nr else None,
            "match": sum(c["match"] * c["n"] for c in chosen) / n,
            "penalty": sum(c["penalty"] for c in chosen), "meets": sum(c["meets"] for c in chosen)}


def fit():
    import itertools

    names = list(RUNS)
    table, missing = responses(names)
    entries = list(table.values())
    cop = HEAT_PUMP_COP
    baseline = score(entries, {}, POLICY_COP)
    chosen, report = {}, {"missing_runs": missing, "types": {}}
    for category, parameters in FIT.items():
        group = [e for e in entries if e["meta"]["category"] == category]
        # The baseline (t = 0) is always a candidate when it lies inside the range.
        grids = {name: [0.0, 1.0] if name == "office_hours" else
                 sorted({round(lo + (hi - lo) * i / GRID, 4) for i in range(GRID + 1)} | ({0.0} if lo <= 0 <= hi else set()))
                 for name, (_, _, lo, hi) in parameters.items()}
        best = None
        for combo in itertools.product(*grids.values()):
            weights = dict(zip(grids, combo))
            o = overall(score(group, {category: weights}, cop), category)
            # Lowest penalty; ties go to the smallest change from the baseline.
            key = (round(o["penalty"], 9), -o["match"], sum(abs(t) for t in combo))
            if best is None or key < best[0]:
                best = (key, weights, o)
        chosen[category] = best[1]
        report["types"][category] = {
            "weights": best[1],
            "values": {name: value_at(category, name, t) for name, t in best[1].items()},
            "baseline": overall(score(group, {}, POLICY_COP), category),
            "cop_only": overall(score(group, {}, cop), category),
            "fitted": best[2],
        }
    fitted = score(entries, chosen, cop)
    diagnostics = {}
    for name in DIAGNOSTIC:
        moved = score(entries, {c: {**chosen.get(c, {}), name: 1.0} for c in FIT}, cop)
        diagnostics[name] = {c: overall(moved, c) for c in FIT} | {"all": overall(moved)}
    report.update(baseline=overall(baseline), fitted=overall(fitted), diagnostics=diagnostics,
                  cohorts=[{"category": k[0], "era": k[1], "baseline": baseline[k], "fitted": fitted[k]}
                           for k in sorted(fitted)],
                  params=fitted_params(chosen))
    return report


# Stage-4 decisions on the hold-out sample (see calibration_plan.md, "Stage 3 results").
# "fitted": the type's whole fitted bundle is accepted; "cop": only the heat-pump COP
# refinement is; the fitted run already carries the COP, so it is not rescaled.
ACCEPTED = {"multi_family": "fitted", "office": "fitted", "single_family": "cop", "school": "cop"}


def decided():
    """Baseline against the accepted changes only, on this sample."""
    table, missing = responses(["fitted"], drop_incomplete=True)
    entries = list(table.values())
    weights = {c: {"fitted": 1.0} for c, how in ACCEPTED.items() if how == "fitted"}
    cop = {c: POLICY_COP if how == "fitted" else HEAT_PUMP_COP for c, how in ACCEPTED.items()}
    base, after = score(entries, {}), score(entries, weights, cop)
    return {"sample": national.OUT.name, "missing_runs": missing, "accepted": ACCEPTED,
            "baseline": overall(base), "accepted_changes": overall(after),
            "types": {c: {"baseline": overall(base, c), "accepted_changes": overall(after, c)} for c in ALL_TYPES},
            "cohorts": [{"category": k[0], "era": k[1], "baseline": base[k], "accepted_changes": after[k]}
                        for k in sorted(after)]}


# A cohort is materially worse when its stage-1 penalty rises by more than two
# buildings in twenty.
MATERIAL = 0.10


def compare():
    """Baseline against the direct fitted run on this sample; acceptance per building type."""
    table, missing = responses(["fitted"], drop_incomplete=True)
    entries = list(table.values())
    base = score(entries, {})
    fitted = score(entries, dict.fromkeys(ALL_TYPES, {"fitted": 1.0}))
    types = {}
    for category in ALL_TYPES:
        b, f = overall(base, category), overall(fitted, category)
        worse = [f"{c} {e}" for (c, e), x in fitted.items()
                 if c == category and x["penalty"] - base[c, e]["penalty"] > MATERIAL + 1e-9]
        types[category] = {"baseline": b, "fitted": f, "materially_worse": worse,
                           "accepted": f["penalty"] < b["penalty"] - 1e-9 and f["above"] <= b["above"]
                           and f["match"] >= b["match"] and not worse}
    return {"sample": national.OUT.name, "missing_runs": missing, "baseline": overall(base),
            "fitted": overall(fitted), "types": types,
            "cohorts": [{"category": k[0], "era": k[1], "baseline": base[k], "fitted": fitted[k]} for k in sorted(fitted)]}


def value_at(category, name, t):
    start, end, _, _ = FIT[category][name]
    return None if start is None else start + t * (end - start)


def fitted_params(chosen):
    """The fitted weights as ``perturbations.apply`` parameters (self-draught as a weight on the step)."""
    params = {"heat_pump_cop": dict.fromkeys(ALL_TYPES, HEAT_PUMP_COP)}
    for category, weights in chosen.items():
        for name, t in weights.items():
            if abs(t) < 1e-9:
                continue
            if name == "setpoint_housing":
                params.setdefault("setpoint_c", {})[category] = round(value_at(category, name, t), 2)
            elif name == "self_draught":
                params.setdefault("self_draught_weight", {})[category] = round(t, 3)
                params.setdefault("self_draught_total_ach", {})[category] = FIT[category][name][1]
            elif name == "office_flow":
                params.setdefault("vent_flow_factor", {})[category] = round(value_at(category, name, t) / 1.3, 4)
            elif name == "office_hours":
                params.setdefault("vent_extra_hours", {})[category] = 1
    return params


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["run", "fit", "compare", "decided"])
    parser.add_argument("--only", nargs="*", help="run names (default: every sensitivity run)")
    parser.add_argument("--params", type=Path, help="parameter JSON for the 'fitted' run")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.step == "fit":
        report = fit()
        out = RESULTS / "fit.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1, default=str) + "\n")
        (out.parent / "fitted_params.json").write_text(json.dumps(report["params"], indent=1) + "\n")
        print(json.dumps({k: report[k] for k in ("baseline", "fitted", "missing_runs")}, indent=1))
        for category, t in report["types"].items():
            print(category, t["values"], t["weights"], "\n  base", t["baseline"], "\n  cop ", t["cop_only"], "\n  fit ", t["fitted"])
        return
    if args.step in ("compare", "decided"):
        report = compare() if args.step == "compare" else decided()
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / f"{args.step}_{national.OUT.name}.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
        after = "fitted" if args.step == "compare" else "accepted_changes"
        print(json.dumps({k: report[k] for k in ("sample", "missing_runs", "baseline", after)}, indent=1))
        for category, t in report["types"].items():
            print(category, {"compare": "accepted" if t.get("accepted") else "rejected"}.get(args.step, ""),
                  t.get("materially_worse", ""), "\n  base", t["baseline"], "\n  new ", t[after])
        return
    names = args.only or list(RUNS)
    extra = json.loads(args.params.read_text()) if args.params else None
    if "fitted" in names and extra is None:
        parser.error("--params is required for the fitted run")
    run(names, args.workers, args.timeout, extra)


if __name__ == "__main__":
    main()
