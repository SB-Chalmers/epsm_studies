"""Tests for robust_score.py.

    python -m pytest validation/catalogue/test_robust_score.py

The baseline tests read the merged-code runs; set MERGED_RUNS and STUDY_OUTPUT to
point elsewhere, and they are skipped when the files are absent. Tests that need
the module's default data files (fgeo.json, results_benchmark/benchmark.json) skip
when those files are absent. The expected
baseline counts are not stored here: set ROBUST_SCORE_EXPECTED to a local JSON file
{"holdout": [match, scored], "templates": [match, scored], "templates_excluded": n};
without it the baseline tests are skipped.
"""

import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

import robust_score as rs

MERGED = Path(os.environ.get("MERGED_RUNS", "/Users/ssanjay/GitHub/epsm_studies/output/merged-rerun-2026-11/DELIVER"))
STUDY = Path(os.environ.get(
    "STUDY_OUTPUT",
    "/Users/ssanjay/GitHub/epsm_studies/.claude/worktrees/catalogue-validation-91f815/output/catalogue_validation"))


def need(path):
    if not Path(path).exists():
        pytest.skip(f"{Path(path).name} not available")


def sample(name):
    need(rs.FGEO_PATH)
    cand = STUDY / f"national_{name}/candidates.jsonl"
    runs = MERGED / f"national_{name}_runs.jsonl"
    if not (cand.exists() and runs.exists()):
        pytest.skip("merged runs not available")
    return rs.Sample(name, rs.load_candidates(cand), rs.last_rows([runs]), rs.load_fgeo())


def expected():
    path = os.environ.get("ROBUST_SCORE_EXPECTED")
    if not path or not Path(path).exists():
        pytest.skip("ROBUST_SCORE_EXPECTED not set")
    return json.loads(Path(path).read_text())


@pytest.mark.parametrize("name", ["holdout", "templates"])
def test_baseline_reproduced(name):
    want = expected()
    s = sample(name)
    assert [sum(s.matches.values()), len(s.ids)] == list(want[name])


def test_templates_exclusion_counted():
    want = expected()
    s = sample("templates")
    assert len(s.excluded) == want["templates_excluded"]
    assert all(r.startswith("error:") for r in s.excluded.values())


def test_identity_permutation_equals_observed():
    s = sample("holdout")
    m = rs.match_matrix(s.S, s.measured[None, :])[0]
    assert m.sum() == sum(s.matches.values())
    m2 = rs.match_matrix(s.S, (s.intensity * s.scale)[None, :])[0]
    assert m2.sum() == m.sum()


def test_permutation_deterministic_and_within_group():
    s = sample("holdout")
    a = rs.chance(s, "type", n=200)
    b = rs.chance(s, "type", n=200)
    assert a == b
    perm = rs.permuted_measured(s, s.cohort, 5, [1, 2]) / s.scale[None, :]
    for row in perm:
        for coh in set(s.cohort):
            idx = [i for i, c in enumerate(s.cohort) if c == coh]
            assert sorted(row[idx]) == pytest.approx(sorted(s.intensity[idx]))


def test_bootstrap_deterministic():
    need(rs.BENCHMARK_PATH)
    s = sample("holdout")
    stock = rs.load_stock()
    assert rs.stock_weighted(s, stock, n=100) == rs.stock_weighted(s, stock, n=100)


def test_mcnemar_hand_computed():
    # gained 8, lost 2: n = 10, P(X <= 2) = (1 + 10 + 45) / 1024; two-sided = 112 / 1024
    assert rs.mcnemar_exact(8, 2) == pytest.approx(112 / 1024)
    assert rs.mcnemar_exact(2, 8) == pytest.approx(112 / 1024)
    assert rs.mcnemar_exact(0, 0) == 1.0
    assert rs.mcnemar_exact(5, 5) == 1.0
    assert rs.mcnemar_exact(6, 0) == pytest.approx(2 / 64)


def test_compare_rule():
    base = {str(i): False for i in range(20)}
    better = {**base, **{str(i): True for i in range(8)}}
    r = rs.compare_samples({"a": (base, better), "b": (base, better)})
    assert r["pooled"] == {"gained": 16, "lost": 0, "mcnemar_p": pytest.approx(2 / 2 ** 16)}
    assert r["accepted"]
    worse_b = {**base, "0": True}
    lost = {**worse_b, "0": False, "1": False}
    r = rs.compare_samples({"a": (base, better), "b": (worse_b, lost)})
    assert not r["gains_in_every_sample"] and not r["accepted"]
    small = {**base, "0": True}
    r = rs.compare_samples({"a": (base, small), "b": (base, small)})
    assert r["gains_in_every_sample"] and not r["accepted"]  # p = 0.5


def test_multifamily_terms():
    c = {"category": "multi_family", "municipality_code": "0331", "epc_atemp_m2": 1000.0,
         "period_start": "2021-01-01", "period_end_exclusive": "2022-01-01", "carrier": "district_heat"}
    fgeo = {"0331": 1.1}
    circ = 25 * (1 / 0.75 - 1)
    assert circ == pytest.approx(25 / 3)
    assert rs.multifamily_terms(c, fgeo) == pytest.approx(1000 * (4.0 * 1.1 + 25 / 3))
    hp = {**c, "carrier": "heat_pump"}
    assert rs.multifamily_terms(hp, fgeo) == pytest.approx(1000 * (4.4 + 25 / 3) / 2.75)
    fuel = {**c, "carrier": "fuel", "period_start": "2020-01-01", "period_end_exclusive": "2021-01-01"}
    assert rs.multifamily_terms(fuel, fgeo) == pytest.approx(1000 * (4.4 + 25 / 3) * 366 / 365 / 0.9)
    assert rs.multifamily_terms({**c, "category": "office"}, fgeo) == 0.0


def test_match_and_position_edges():
    assert rs.is_match({"a": 1.2})
    assert rs.is_match({"a": 0.8})
    assert not rs.is_match({"a": 1.21, "b": 0.79})
    assert rs.position({"a": 1.21, "b": 0.79}) == "between"
    assert rs.position({"a": 1.3, "b": 1.5}) == "above"
    assert rs.position({"a": 0.5}) == "below"
    assert rs.is_match({"a": 2.0}, scale=0.5)


def test_wilson():
    # 50 of 100: centre 0.5, half-width z*sqrt(0.25/100 + z^2/40000) / (1 + z^2/100)
    z = 1.959963984540054
    half = z * math.sqrt(0.25 / 100 + z * z / 40000) / (1 + z * z / 100)
    lo, hi = rs.wilson(50, 100)
    assert lo == pytest.approx(0.5 - half) and hi == pytest.approx(0.5 + half)
    assert lo == pytest.approx(0.4038, abs=1e-3)
    assert rs.wilson(0, 0) == (None, None)


def test_oracle_scale_one_when_already_best():
    class S:
        name = "x"
        ids = ["a", "b"]
        cohort = ["c", "c"]
        ratios = {"a": {"s": 1.0}, "b": {"s": 1.0}}
    assert rs.fit_cohort_scales(S()) == {"c": pytest.approx(1.0, abs=2e-3)}
    assert not math.isnan(np.log(rs.ORACLE_GRID).min())
