import csv
import json
import math
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from epsm_studies import PaperStudy, compare_energy_results, write_comparison_report


AXIS = tuple(datetime(2023, 1, 31, 22) + timedelta(hours=i) for i in range(4))
IDENTITY = {"building_snapshot_sha256": "a"*64,
            "physical_inputs_sha256": "b"*64, "weather_sha256": "c"*64}
SIGNAL = "space_heating_demand_kwh"


def result(values):
    return SimpleNamespace(run_id="run-id", units={SIGNAL: "kWh"}, time_axis=AXIS,
        hourly={SIGNAL: list(values)}, scalars={SIGNAL: sum(values)},
        diagnostics={"accepted": True, "physical_inputs_sha256": IDENTITY["physical_inputs_sha256"]})


def compare(reference=None, candidate=None, **changes):
    options = dict(reference_identity=IDENTITY, candidate_identity=IDENTITY,
                   expected_time_axis=AXIS)
    return compare_energy_results(reference or result([1, 2, 3, 4]),
        candidate or result([2, 4, 6, 8]), **{**options, **changes})


def test_annual_hourly_peak_monthly_and_reference_direction():
    report = compare()
    assert report["reference_kwh"] == 10
    assert report["candidate_kwh"] == 20
    assert report["difference_percent"] == 100
    assert report["candidate_peak_kw"] == 8
    assert report["peak_difference_percent"] == 100
    assert report["hourly_mae_kwh"] == 2.5
    assert report["hourly_rmse_kwh"] == pytest.approx(math.sqrt(7.5))
    assert report["hourly_correlation"] == pytest.approx(1)
    assert report["monthly"] == {"2023-01": {"reference_kwh": 3, "candidate_kwh": 6},
                                  "2023-02": {"reference_kwh": 7, "candidate_kwh": 14}}


def test_zero_reference_has_undefined_relative_error_and_correlation():
    report = compare(result([0]*4))
    assert report["difference_percent"] is None
    assert report["peak_difference_percent"] is None
    assert report["hourly_correlation"] is None


def test_complete_leap_year_is_preserved_without_truncation():
    axis = tuple(datetime(2024, 1, 1) + timedelta(hours=i) for i in range(8784))
    first = result([1]*len(axis))
    second = result([2]*len(axis))
    first.time_axis = second.time_axis = axis
    report = compare(first, second, expected_time_axis=axis)
    assert report["hours"] == 8784
    assert report["monthly"]["2024-02"]["reference_kwh"] == 29*24
    assert len(report["hourly"]) == 8784


@pytest.mark.parametrize("key", IDENTITY)
def test_different_inputs_never_become_an_engine_accuracy_statistic(key):
    with pytest.raises(ValueError, match="identities differ"):
        compare(candidate_identity={**IDENTITY, key: "d"*64})


@pytest.mark.parametrize("change,match", [
    ("rejected", "accepted"), ("missing_hour", "calendar"),
    ("shifted", "calendar"), ("nonfinite", "finite"),
    ("unbalanced", "accounting"), ("wrong_unit", "units"),
    ("wrong_identity", "diagnostics"), ("short_values", "complete"),
])
def test_invalid_engine_results_do_not_enter_report(change, match):
    bad = result([1, 2, 3, 4])
    if change == "rejected":
        bad.diagnostics["accepted"] = False
    elif change == "missing_hour":
        bad.time_axis = AXIS[:-1]
    elif change == "shifted":
        bad.time_axis = tuple(t + timedelta(hours=1) for t in AXIS)
    elif change == "nonfinite":
        bad.hourly[SIGNAL][0] = float("nan")
    elif change == "unbalanced":
        bad.scalars[SIGNAL] = 1000
    elif change == "wrong_unit":
        bad.units[SIGNAL] = "W"
    elif change == "wrong_identity":
        bad.diagnostics["physical_inputs_sha256"] = "f"*64
    elif change == "short_values":
        bad.hourly[SIGNAL].pop()
    with pytest.raises(ValueError, match=match):
        compare(candidate=bad)


def test_expected_calendar_is_itself_continuous():
    with pytest.raises(ValueError, match="continuous"):
        compare(expected_time_axis=(AXIS[0], AXIS[2]))


def test_files_retain_failed_cases_escape_text_and_never_overwrite(tmp_path):
    study = PaperStudy("<script>alert('x')</script>", "Question")
    cases = [{"case_id": "valid", "comparison": compare(), "assumptions": "<unsafe>"},
             {"case_id": "unsupported", "error": "unsupported geometry <unsafe>"}]
    paths = write_comparison_report(study, cases, tmp_path,
        reference_label="EnergyPlus", candidate_label="RC")
    payload = json.loads(paths["json"].read_text())
    assert payload["complete"] is False
    assert "hourly" not in payload["cases"][0]["comparison"]
    assert payload["cases"][1]["error"].startswith("unsupported")
    text = paths["html"].read_text()
    assert "<script>" not in text and "&lt;unsafe&gt;" in text
    assert "FAILED" in text and "Incomplete" in text
    with paths["csv"].open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4 and all(row["case_id"] == "valid" for row in rows)
    with pytest.raises(FileExistsError):
        write_comparison_report(study, cases, tmp_path, reference_label="E+", candidate_label="RC")


def test_report_requires_unique_cases_and_explicit_outcomes(tmp_path):
    study = PaperStudy("Test", "Question")
    with pytest.raises(ValueError, match="unique"):
        write_comparison_report(study, [], tmp_path, reference_label="E+", candidate_label="RC")
    with pytest.raises(ValueError, match="explicit error"):
        write_comparison_report(study, [{"case_id": "missing"}], tmp_path,
                                reference_label="E+", candidate_label="RC")
