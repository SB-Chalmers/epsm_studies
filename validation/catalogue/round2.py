"""Round 2 of ``calibration_plan.md``: sourced template choices, fixed before scoring.

    python validation/catalogue/round2.py estimate     # calibration, linear from stage-3 responses
    python validation/catalogue/round2.py run --workers 13   # direct rerun of the chosen setpoints
    python validation/catalogue/round2.py score        # direct rerun against the current model
    python validation/catalogue/round2.py terms        # post-processing terms against the current model
    python validation/catalogue/round2.py area         # the current model scored per m² as well as in total

Set ``VALIDATION_OUT`` to the hold-out output for ``run``, ``score``, ``terms`` and ``area``.

Tests (fixed in advance):

1. BETSI measured indoor temperature by era (Boverket 2010, tables 3.3 and 3.6) replaces
   the fitted 23.0 °C for multifamily and is tried for single-family. SE.06 and SE.07,
   built after the survey, take the newest measured class (1996–2005); the stock mean is
   reported as a sensitivity. Single-family is also tried with the BETSI 0.40 ACH
   self-draught.
2. Hot-water circulation from the catalogue's own Sveby 2.0 hot water (21 kWh/m², table
   8.1) instead of BEN's 25: 7.0 against 8.3 kWh/m².
3. Window airing for schools: Sveby *Brukarindata undervisning* 1.0, table 2.2, adds
   4 kWh/m² Atemp per year in post-processing.
4. Area: each ratio multiplied by EPC Atemp / model conditioned area, to show how much of a
   cohort's bias follows from the model conditioning more floor than the EPC heats.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ.setdefault("VALIDATION_OUT", str(ROOT / "output/catalogue_validation/national_templates"))
sys.path.insert(0, str(HERE))
import national_three_state as national  # noqa: E402
import sensitivity as sens  # noqa: E402

RESULTS = HERE / "results_round2"

# Boverket (2010), Energi i bebyggelsen (BETSI), table 3.3 (småhus) p. 62 and table 3.6
# (lägenheter i flerbostadshus) p. 66: mean measured indoor temperature by construction year.
BETSI_SETPOINT = {
    "single_family": {"SE.01": 20.8, "SE.02": 21.3, "SE.03": 21.7, "SE.04": 21.4, "SE.05": 21.9},
    "multi_family": {"SE.01": 22.2, "SE.02": 22.6, "SE.03": 22.5, "SE.04": 22.4, "SE.05": 23.0},
}
BETSI_STOCK = {"single_family": 21.2, "multi_family": 22.4}
SVEBY_SETPOINT = 21.0
# The stage-3 one-at-a-time setpoint run: multifamily 23.0, single-family 21.9 °C.
RUN_SETPOINT = {"multi_family": 23.0, "single_family": 21.9}

SVEBY_DHW_KWH_M2 = 21.0  # Sveby Brukarindata bostadshus 2.0, table 8.1 (sveby_residential_v2.json)
SCHOOL_AIRING_KWH_M2 = 4.0  # Sveby Brukarindata undervisning 1.0, table 2.2 (sveby_school_v1.json)


def setpoint(category, era, post_2005="newest"):
    table = BETSI_SETPOINT[category]
    if era in table:
        return table[era]
    return table["SE.05"] if post_2005 == "newest" else BETSI_STOCK[category]


def area_factors():
    """EPC Atemp / model conditioned area per building, from the sample's buildings.csv."""
    name = {"national_templates": "results_national_templates",
            "national_holdout": "results_national_holdout"}[national.OUT.name]
    with open(HERE / name / "buildings.csv") as f:
        return {r["building_id"]: float(r["atemp_to_geometry"]) for r in csv.DictReader(f)
                if r["atemp_to_geometry"]}


def per_area(entries):
    """Copies whose measured heating is rescaled to the model's conditioned area."""
    factors = area_factors()
    scaled = []
    for e in entries:
        f = factors.get(e["meta"]["building_id"])
        if f:
            scaled.append(e | {"meta": e["meta"] | {"measured_kwh": e["meta"]["measured_kwh"] / f}})
    return scaled


def accept(base, new, name):
    return sens._accept(base, new, name, {})


def estimate():
    """Calibration only: per-era setpoints from the stage-3 setpoint response, taken linearly
    (the stage-3 fit predicted its direct rerun within 0.4 points)."""
    table, missing = sens.responses(["setpoint_housing", "self_draught", "fitted", "bridges"], drop_incomplete=True)
    entries = list(table.values())
    weights, cop = sens.current_config(entries)
    out = {"sample": national.OUT.name, "missing_runs": missing, "tests": {}}
    linear_current = {**weights, "multi_family": {"setpoint_housing": 1.0, "self_draught": 1.0, "airing": 1.0, "vvc": 1.0}}
    # The one-at-a-time runs are at the policy COP; the current model carries the field average.
    linear_cop = {**cop, "multi_family": sens.HEAT_PUMP_COP}
    variants = {}
    for post in ("newest", "stock"):
        for e in entries:
            m = e["meta"]
            if m["category"] in RUN_SETPOINT:
                t = (setpoint(m["category"], m["era"], post) - SVEBY_SETPOINT) / (RUN_SETPOINT[m["category"]] - SVEBY_SETPOINT)
                e[f"betsi_{post}"] = {s: t * d for s, d in e["setpoint_housing"].items()}
        variants[f"mf_betsi_{post}"] = (linear_current, {
            **linear_current, "multi_family": {f"betsi_{post}": 1.0, "self_draught": 1.0, "airing": 1.0, "vvc": 1.0}}, linear_cop)
        variants[f"sf_betsi_{post}"] = (weights, {**weights, "single_family": {f"betsi_{post}": 1.0}}, cop)
        variants[f"sf_betsi_{post}_draught"] = (
            weights, {**weights, "single_family": {f"betsi_{post}": 1.0, "self_draught": 1.0}}, cop)
    for name, (before, after, c) in variants.items():
        result = {}
        for basis, group in (("total", entries), ("per_area", per_area(entries))):
            result[basis] = accept(sens.score(group, before, c), sens.score(group, after, c), name)
        out["tests"][name] = result
    return out


def run_params(post_2005="newest"):
    """The direct-rerun parameters: the current model with multifamily setpoints by era."""
    params = sens.bridge_params()
    params["thermal_bridge_delta_u"] = {c: v for c, v in params["thermal_bridge_delta_u"].items()
                                        if c in sens.BRIDGES_ACCEPTED}
    params["setpoint_c"] = {"multi_family": {era: setpoint("multi_family", era, post_2005)
                                             for era in sens.shared.ERAS}}
    return params


def score_direct():
    """The current model against the same model with BETSI setpoints by era (direct run)."""
    sens.RUNS["betsi"] = (None, ("multi_family",), sens.ALL_STATES)
    table, missing = sens.responses(["fitted", "bridges", "betsi"], drop_incomplete=True)
    entries = list(table.values())
    weights, cop = sens.current_config(entries)
    new = {**weights, "multi_family": {"betsi": 1.0, "airing": 1.0, "vvc": 1.0}}
    # The betsi run is multifamily only and carries its current changes and COP.
    out = {"sample": national.OUT.name, "missing_runs": missing}
    for basis, group in (("total", entries), ("per_area", per_area(entries))):
        out[basis] = accept(sens.score(group, weights, cop), sens.score(group, new, cop), "betsi")
    return out


def terms():
    entries, missing, weights, cop = sens._current_entries()
    out = {"sample": national.OUT.name, "missing_runs": missing, "tests": {}}
    for e in entries:
        m = e["meta"]
        e["vvc_sveby"] = dict.fromkeys(e["base"], sens.term_kwh(m, SVEBY_DHW_KWH_M2 * (1 / 0.75 - 1))
                                       if m["category"] == "multi_family" else 0.0)
        e["school_airing"] = dict.fromkeys(e["base"], sens.term_kwh(m, SCHOOL_AIRING_KWH_M2)
                                           if m["category"] == "school" else 0.0)
    without_vvc = {c: {k: t for k, t in w.items() if k != "vvc"} for c, w in weights.items()}
    variants = {
        # Circulation on the catalogue's own hot water, judged as revision 4 was: against no circulation.
        "vvc_sveby": (without_vvc, {**without_vvc, "multi_family": {**without_vvc["multi_family"], "vvc_sveby": 1.0}}),
        "vvc_ben": (without_vvc, weights),
        "school_airing": (weights, {**weights, "school": {**weights.get("school", {}), "school_airing": 1.0}}),
    }
    for name, (before, after) in variants.items():
        out["tests"][name] = {basis: accept(sens.score(g, before, cop), sens.score(g, after, cop), name)
                              for basis, g in (("total", entries), ("per_area", per_area(entries)))}
    return out


def area():
    """The stage-3 baseline and the current model, scored in total and per m²."""
    entries, missing, weights, cop = sens._current_entries()
    out = {"sample": national.OUT.name, "missing_runs": missing}
    for basis, group in (("total", entries), ("per_area", per_area(entries))):
        out[basis] = accept(sens.score(group, {}), sens.score(group, weights, cop), "current")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["estimate", "run", "score", "terms", "area"])
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    if args.step == "run":
        sens.RUNS["betsi"] = (run_params(), ("multi_family",), sens.ALL_STATES)
        sens.run(["betsi"], args.workers, args.timeout)
        return
    result = {"estimate": estimate, "score": score_direct, "terms": terms, "area": area}[args.step]()
    path = RESULTS / f"{args.step}_{national.OUT.name}.json"
    path.write_text(json.dumps(result, indent=1, default=str))
    print(path)


if __name__ == "__main__":
    main()
