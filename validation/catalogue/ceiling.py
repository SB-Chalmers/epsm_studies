"""How much better can match get? Two oracle ceilings against the current model, per cohort.

A building matches when one state's simulated heating is within ±20 % of the measured
value (``shared.classify``). On the current accepted model (stage 3, plus the office
thermal bridges), compare:

- ``current``: the share that matches now;
- ``levels``: the best possible share if each state were one fixed intensity per cohort
  (three levels, one for SE.07), placed with full knowledge of the measured values. This
  is the most an archetype without building-specific variation could reach;
- ``scaled``: the best possible share if each state of the current simulations were
  multiplied by its own per-cohort factor, chosen with full knowledge of the measured
  values. This keeps the model's building-to-building variation and is an overfit
  upper bound for re-tuning the archetypes alone.

Both are in-sample oracles. ``--apply-from`` takes the levels and factors chosen on
another sample (the calibration run's JSON) and scores them here, which is what fully
fitted archetypes would reach on buildings they were not fitted to. ``one_level`` is the
best single fixed intensity: the within-cohort spread one state can cover at all.

    python validation/catalogue/ceiling.py          # VALIDATION_OUT selects the sample
    VALIDATION_OUT=.../national_holdout python validation/catalogue/ceiling.py \
        --apply-from results_sensitivity/ceiling_national_templates.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sensitivity  # noqa: E402

BAND = math.log((1 + sensitivity.shared.MATCH_TOLERANCE) / (1 - sensitivity.shared.MATCH_TOLERANCE))


def windows(values):
    """{factor: bitmask} for each best-aligned window of log-width BAND (a point on its lower
    edge). A level or factor ``f`` matches value ``v`` when f/v is within ±tolerance."""
    tol = sensitivity.shared.MATCH_TOLERANCE
    logs = [math.log(v) for v in values]
    return {round(math.exp(x) * (1 + tol), 6): sum(1 << j for j, y in enumerate(logs) if x <= y <= x + BAND + 1e-12)
            for x in logs}


def best(windows_per_state):
    """Largest union of one window per state, and the factor chosen for each state."""
    top = (-1, None)
    for combo in itertools.product(*(w.items() for w in windows_per_state)):
        mask = 0
        for _, m in combo:
            mask |= m
        count = bin(mask).count("1")
        if count > top[0]:
            top = (count, [f for f, _ in combo])
    return top


def matched(values_per_state, factors):
    tol = sensitivity.shared.MATCH_TOLERANCE
    return sum(any(abs(f / v - 1) <= tol for f, v in zip(factors, values)) for values in zip(*values_per_state))


def current_ratios(entry, config):
    weights, cop = config
    return sensitivity.ratios(entry, weights.get(entry["meta"]["category"], {}), cop)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply-from", type=Path, help="ceiling JSON from another sample")
    args = parser.parse_args()
    chosen = {}
    if args.apply_from:
        chosen = {(r["category"], r["era"]): r for r in json.loads(args.apply_from.read_text())["cohorts"]}
    table, missing = sensitivity.responses(["fitted", "bridges"], drop_incomplete=True)
    config = sensitivity.current_config(table.values())
    cohorts = {}
    for e in table.values():
        m = e["meta"]
        intensity = m["measured_kwh"] / m["epc_atemp_m2"] * (sensitivity.HEAT_PUMP_COP if m["carrier"] == "heat_pump" else 1)
        cohorts.setdefault((m["category"], m["era"]), []).append((current_ratios(e, config), intensity))
    measures = ["current", "one_level", "levels", "scaled"] + (["levels_oos", "scaled_oos"] if chosen else [])
    rows = []
    for (category, era), items in sorted(cohorts.items()):
        states = list(items[0][0])
        intensities = [m for _, m in items]
        inverse = [[1 / r[s] for r, _ in items] for s in states]  # k*r_s within band <=> k vs 1/r_s
        levels, level_values = best([windows(intensities)] * len(states))
        scaled, factors = best([windows(v) for v in inverse])
        row = {"category": category, "era": era, "n": len(items),
               "current": sum(sensitivity.shared.classify(r)[1] is not None for r, _ in items),
               "one_level": best([windows(intensities)])[0], "levels": levels, "scaled": scaled,
               "level_values": level_values, "factors": dict(zip(states, factors))}
        if chosen:
            other = chosen.get((category, era))
            row["levels_oos"] = matched([intensities] * len(states), other["level_values"]) if other else None
            row["scaled_oos"] = matched(inverse, [other["factors"][s] for s in states]) if other else None
        rows.append(row)

    def share(selected):
        n = sum(r["n"] for r in selected)
        return {"n": n} | {k: sum(r[k] for r in selected) / n for k in measures if all(r.get(k) is not None for r in selected)}

    report = {"sample": sensitivity.national.OUT.name, "applied_from": str(args.apply_from or ""), "missing_runs": missing,
              "overall": share(rows), "types": {c: share([r for r in rows if r["category"] == c]) for c in sensitivity.ALL_TYPES},
              "cohorts": rows}
    out = sensitivity.RESULTS / f"ceiling_{sensitivity.national.OUT.name}.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    for name, t in [("all", report["overall"])] + list(report["types"].items()):
        print(f"{name:14}", " ".join(f"{k} {v:.0%}" if k != "n" else f"n={v}" for k, v in t.items()))
    for r in rows:
        print(f"{r['category']:14} {r['era']} n={r['n']:2}", " ".join(
            f"{k} {r[k] / r['n']:.0%}" for k in measures if r.get(k) is not None))


if __name__ == "__main__":
    main()
