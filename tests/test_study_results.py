"""Retained result evidence survives retries, partial failures and relocation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from epsm_studies import Study, StudySpec, StudyResults

pytest.importorskip("epsm_workflows", reason="Archive collection requires the optional Workflows integration")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_bundle(root, *, evaluation_id="evaluation-1", lca_status="complete", values=(1., 2., 3., 4.), annual=False):
    root.mkdir(parents=True)
    (root / "arrays").mkdir()
    signal = "space_heating_demand_kwh"
    np.save(root / "arrays/heating.npy", values, allow_pickle=False)
    axis = np.arange("2023-01-01", "2024-01-01", dtype="datetime64[h]").astype("U13") if annual else ["2023-01-31T22", "2023-01-31T23", "2023-02-01T00", "2023-02-01T01"]
    np.save(root / "arrays/time.npy", axis, allow_pickle=False)
    data = {
        "id": evaluation_id, "state_id": "a" * 64, "energy_id": "b" * 64, "lca_id": "c" * 64,
        "engine": "epsm_rc", "weather": {"sha256": "d" * 64, "calendar_year": 2023},
        "energy": {"engine": "epsm_rc", "run_id": "engine-run", "scalars": {signal: sum(values)},
                   "hourly_signals": [signal], "units": {signal: "kWh"},
                   "diagnostics": {"accepted": True, "physical_inputs_sha256": "e" * 64},
                   "artifacts": {}, "delivered_by_carrier": {"electricity": sum(values)},
                   "requirements": [], "boundary": "space_heating_and_fans", "annual": annual},
        "lca": {"format": "epsm-lca-result/2", "status": lca_status,
                "material_gwp_kgco2e": 50. if lca_status == "complete" else None,
                "operational_gwp_kgco2e": 10. if lca_status == "complete" else None,
                "total_gwp_kgco2e": 60. if lca_status == "complete" else None,
                "requirements": [] if lca_status == "complete" else ["Missing material factor"],
                "assessment": {"reference_period_years": 30}, "contributions": []},
    }
    metadata = root / "metadata.json"
    metadata.write_text(json.dumps(data))
    def ref(path):
        return {"path": str(path.relative_to(root)), "sha256": _sha(path),
                "shape": [len(values)], "dtype": "float64" if path.name == "heating.npy" else "<U13"}
    manifest = {"format": "epsm-evaluation-bundle/1", "evaluation_id": evaluation_id,
                "metadata": {"path": "metadata.json", "sha256": _sha(metadata)},
                "arrays": {"hourly": {signal: ref(root / "arrays/heating.npy")},
                           "time_axis": ref(root / "arrays/time.npy")}, "artifacts": {}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    return data


def fixture_evaluate(payload):
    if payload.get("fail"):
        raise RuntimeError("Declared fixture failure")
    root = Path(payload["_execution"]["directory"])
    path = root / "artifacts" / payload["_execution"]["case_id"] / payload["_execution"]["attempt_id"] / "evaluation"
    annual = payload.get("annual", False)
    make_bundle(path, evaluation_id=payload["name"], lca_status=payload.get("lca_status", "complete"),
                values=[1.] * 8760 if annual else [1., 2., 3., 4.], annual=annual)
    reference = {"format": "epsm-evaluation-reference/1", "path": str(path.relative_to(root))}
    if annual:
        lca_complete = payload.get("lca_status", "complete") == "complete"
        reference["coverage"] = {"ready": lca_complete, "thermal_complete": True,
            "delivery_complete": True, "lca_complete": lca_complete, "diagnostics": []}
    return reference


def prepared(tmp_path, *, partial=False, annual=False):
    from epsm_workflows import PreparedEvaluation, prepare
    from epsm_workflows.execution import run_case
    cases = [PreparedEvaluation(payload={"name": "first"}, inputs={"axes": {
        "subject_id": "building-1", "scenario_id": "baseline", "sample_id": "0", "engine": "epsm_rc", "weather_id": "w"}}, name="first")]
    if partial:
        cases.extend([
            PreparedEvaluation(payload={"name": "second", "lca_status": "incomplete"}, inputs={"axes": {"subject_id": "building-2", "engine": "epsm_rc", "sample_id": "0", "scenario_id": "baseline", "weather_id": "w"}}, name="second"),
            PreparedEvaluation(payload={"name": "failed", "fail": True}, inputs={"axes": {"subject_id": "building-3"}}, name="failed"),
            PreparedEvaluation(payload={"name": "pending"}, inputs={"axes": {"subject_id": "building-4"}}, name="pending"),
        ])
    if annual:
        for case in cases:
            case.payload["annual"] = True
    plan = tmp_path / "execution"
    prepare(plan, cases, handler="test_study_results:fixture_evaluate")
    run_case(plan, 0)
    if partial:
        run_case(plan, 1)
        run_case(plan, 2)
    spec = StudySpec("Result evidence", workflow={"format": "epsm-workflow/1", "outputs": [
        {"name": "space_heating_demand_kwh", "resolution": "hourly", "required": True, "unit": "kWh"},
        {"name": "lca", "resolution": "assessment", "required": True}]})
    return spec, plan


def test_portable_archive_preserves_planned_rows_and_partial_assessments(tmp_path):
    spec, plan = prepared(tmp_path, partial=True)
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    assert result.spec.id == spec.id
    assert len(result.table()) == 4
    coverage = result.coverage()
    assert coverage["total"] == 4
    assert coverage["succeeded"] == 2
    assert coverage["failed"] == 1
    assert coverage["not_run"] == 1
    assert coverage["complete"] is False
    assert coverage["outputs"]["lca"]["available"] == 1
    assert result.select(subject_id="building-2")[0]["lca_status"] == "incomplete"
    assert result.hourly(0, "space_heating_demand_kwh").tolist() == [1, 2, 3, 4]
    assert result.evaluation_metadata(1)["lca"]["requirements"] == ["Missing material factor"]
    with pytest.raises(ValueError, match="successful"):
        result.hourly(2, "space_heating_demand_kwh")
    assert StudyResults.collect(spec, plan, tmp_path / "archive").id == result.id
    moved = tmp_path / "moved"
    shutil.move(tmp_path / "archive", moved)
    shutil.rmtree(plan)
    restored = StudyResults.open(moved)
    assert restored.hourly(0, "space_heating_demand_kwh").sum() == 10
    assert Study.open(moved).spec.id == spec.id
    restored.verify()


def test_metadata_inspection_is_lazy_and_reopens_without_execution_dependencies(tmp_path, monkeypatch):
    spec, plan = prepared(tmp_path)
    root = tmp_path / "archive"
    StudyResults.collect(spec, plan, root)
    def forbidden(*args, **kwargs):
        raise AssertionError("Hourly array loaded during metadata inspection")
    monkeypatch.setattr(np, "load", forbidden)
    results = StudyResults.open(root)
    assert results.coverage()["total"] == 1
    assert len(results.select(engine="epsm_rc")) == 1
    assert len(repr(results)) <= 160
    script = r'''
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'epsm', 'epsm_workflows', 'epsm_core', 'epsm_rc', 'numpy'}:
            raise RuntimeError('Execution import: ' + fullname)
sys.meta_path.insert(0, Block())
from epsm_studies import Study, StudyResults
results = StudyResults.open(sys.argv[1])
assert results.coverage()['total'] == 1
assert Study.open(sys.argv[1]).spec.name == 'Result evidence'
assert results.table()[0]['evaluation_id'] == 'first'
'''
    proc = subprocess.run([sys.executable, "-c", script, str(root)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_changed_array_fails_explicit_read_and_full_verification(tmp_path):
    spec, plan = prepared(tmp_path)
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    path = next((tmp_path / "archive").rglob("heating.npy"))
    np.save(path, [999., 2., 3., 4.], allow_pickle=False)
    assert StudyResults.open(tmp_path / "archive").coverage()["total"] == 1
    with pytest.raises(ValueError, match="[Cc]hanged|checksum"):
        result.hourly(0, "space_heating_demand_kwh")
    with pytest.raises(ValueError, match="[Cc]hanged|checksum"):
        result.verify()


def test_archive_keeps_earlier_retry_evidence_and_refuses_changed_recollection(tmp_path):
    from epsm_workflows.execution import run_case
    spec, plan = prepared(tmp_path, partial=True)
    first = StudyResults.collect(spec, plan, tmp_path / "archive")
    failed = first.table()[2]["attempt_id"]
    run_case(plan, 2, retry_failed=True)
    with pytest.raises(FileExistsError):
        StudyResults.collect(spec, plan, tmp_path / "archive")
    second = StudyResults.collect(spec, plan, tmp_path / "archive-2")
    assert second.id != first.id
    attempts = second.attempts(2)
    assert len(attempts) == 2
    assert failed in {r["id"] for r in attempts}
    assert first.table()[2]["attempt_id"] == failed


def test_archive_rejects_escaping_bundle_and_incomplete_publication(tmp_path):
    spec, plan = prepared(tmp_path)
    outside = tmp_path / "outside"
    make_bundle(outside)
    result_path = plan / "results/000000.json"
    row = json.loads(result_path.read_text())
    row["result"]["path"] = "../outside"
    row.pop("record_sha256")
    from epsm_workflows.records import digest
    row["record_sha256"] = digest(row)
    result_path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="escapes"):
        StudyResults.collect(spec, plan, tmp_path / "archive")
    root = tmp_path / "incomplete"
    root.mkdir()
    with pytest.raises(ValueError, match="completed"):
        StudyResults.open(root)
    assert not (tmp_path / "archive").exists()


def test_general_helpers_keep_units_boundaries_and_incomplete_coverage_visible(tmp_path):
    spec, plan = prepared(tmp_path, partial=True, annual=True)
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    months = results.aggregate_energy(0, period="monthly")
    assert months["2023-01"] == 744.
    assert months["2023-02"] == 672.
    assert sum(months.values()) == 8760.
    assert results.aggregate_energy(0, period="annual") == {"2023": 8760.}
    totals = results.portfolio_total("space_heating_demand_kwh", case_ids=[0, 1])
    assert totals["value"] == 17520
    assert totals["unit"] == "kWh"
    assert totals["complete"] is True
    incomplete = results.portfolio_total("material_gwp_kgco2e", case_ids=[0, 1])
    assert incomplete["value"] is None
    assert incomplete["known_subtotal"] == 50
    assert incomplete["complete"] is False
    difference = results.difference(0, 0, "space_heating_demand_kwh")
    assert difference["difference"] == 0
    assert difference["difference_percent"] == 0
    with pytest.raises(ValueError, match="distinct"):
        results.portfolio_total("space_heating_demand_kwh", case_ids=[0, 0])
    with pytest.raises(ValueError, match="period"):
        results.aggregate_energy(0, period="weekly")
    csv_path = results.export(tmp_path / "results.csv")
    text = csv_path.read_text()
    assert "case_id" in text and "building-4" in text and "not_run" in text
    with pytest.raises(FileExistsError):
        results.export(csv_path)


def test_baseline_differences_do_not_treat_missing_impacts_as_zero(tmp_path):
    spec, plan = prepared(tmp_path, partial=True)
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    with pytest.raises(ValueError, match="same subject"):
        results.difference(0, 1, "material_gwp_kgco2e")
    value = results.difference(1, 1, "material_gwp_kgco2e")
    assert value["difference"] is None
    assert value["difference_percent"] is None
    assert value["complete"] is False


def test_engine_comparison_adapter_preserves_strict_owner_identities(tmp_path):
    spec, plan = prepared(tmp_path)
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    expected = ["2023-01-31T22", "2023-01-31T23", "2023-02-01T00", "2023-02-01T01"]
    comparison = results.compare_engines(0, 0, expected_time_axis=expected)
    assert comparison["reference_run_id"] == "engine-run"
    assert comparison["difference_kwh"] == 0
    with pytest.raises(ValueError, match="complete expected"):
        results.compare_engines(0, 0, expected_time_axis=expected[:-1])


def test_frozen_workflow_link_refuses_attaching_a_changed_draft(tmp_path):
    spec, plan = prepared(tmp_path)
    # This source was created through the generic legacy prepare API. A retained
    # owner specification makes an intentionally different authoring record clear.
    (plan / "workflow.json").write_text(json.dumps({"format": "epsm-workflow/1", "changed": True}))
    with pytest.raises(ValueError, match="workflow differs"):
        StudyResults.collect(spec, plan, tmp_path / "archive")
    assert not (tmp_path / "archive").exists()


def test_cli_inspection_and_export_use_the_same_archive_api(tmp_path):
    spec, plan = prepared(tmp_path)
    archive = tmp_path / "archive"
    StudyResults.collect(spec, plan, archive)
    inspected = subprocess.run([sys.executable, "-m", "epsm_studies", "inspect", str(archive), "--verify"],
                               capture_output=True, text=True)
    assert inspected.returncode == 0, inspected.stderr
    assert json.loads(inspected.stdout)["total"] == 1
    exported = subprocess.run([sys.executable, "-m", "epsm_studies", "export", str(archive), str(tmp_path / "table.csv")],
                              capture_output=True, text=True)
    assert exported.returncode == 0, exported.stderr
    assert "first" in (tmp_path / "table.csv").read_text()
    rejected = subprocess.run([sys.executable, "-m", "epsm_studies", "export", str(archive), str(tmp_path / "table.csv")],
                              capture_output=True, text=True)
    assert rejected.returncode == 2
    assert "Traceback" not in rejected.stderr


def test_bundle_reference_manifest_identity_and_owner_coverage_are_retained(tmp_path):
    spec, plan = prepared(tmp_path)
    path = plan / "results/000000.json"
    row = json.loads(path.read_text())
    bundle = plan / row["result"]["path"]
    row["result"].update(manifest_sha256=_sha(bundle / "manifest.json"), evaluation_id="first", coverage={
        "ready": False, "thermal_complete": False, "delivery_complete": False,
        "lca_complete": True, "diagnostics": [{"code": "calendar", "field": "energy.time_axis", "severity": "error"}]})
    from epsm_workflows.records import digest
    row.pop("record_sha256")
    row["record_sha256"] = digest(row)
    path.write_text(json.dumps(row))
    (plan / "attempts/000000" / f"{row['id']}.json").write_text(json.dumps(row))
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    assert result.coverage()["outputs"]["space_heating_demand_kwh"]["available"] == 0
    assert result.coverage()["complete"] is False
    assert result.table()[0]["producer_coverage"]["diagnostics"][0]["code"] == "calendar"
    (bundle / "manifest.json").write_text((bundle / "manifest.json").read_text() + "\n")
    with pytest.raises(ValueError, match="manifest checksum"):
        StudyResults.collect(spec, plan, tmp_path / "archive-2")


def test_explicit_reads_check_the_archived_bundle_manifest_not_only_array_hashes(tmp_path):
    spec, plan = prepared(tmp_path)
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    entry = results.table()[0]
    manifest = results.directory / entry["bundle"] / "manifest.json"
    manifest.write_text(manifest.read_text() + "\n")
    with pytest.raises(ValueError, match="manifest checksum"):
        results.hourly(0)


def _change_bundle_metadata(plan, index, change):
    row = json.loads((plan / f"results/{index:06d}.json").read_text())
    bundle = plan / row["result"]["path"]
    metadata_path = bundle / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    change(metadata)
    metadata_path.write_text(json.dumps(metadata))
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["metadata"]["sha256"] = _sha(metadata_path)
    manifest_path.write_text(json.dumps(manifest))


def test_legacy_structural_availability_never_claims_verified_study_completeness(tmp_path):
    spec, plan = prepared(tmp_path)
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    assert result.coverage()["outputs"]["space_heating_demand_kwh"]["available"] == 1
    assert result.coverage()["complete"] is False
    assert result.coverage()["unverified_results"] == 1
    assert result.table()[0]["coverage_verified"] is False


def test_nonadditive_metrics_and_mixed_calendar_years_cannot_form_portfolio_totals(tmp_path):
    spec, plan = prepared(tmp_path, partial=True)
    for index in (0, 1):
        def add_temperature(data):
            data["weather"]["calendar_year"] = 2023
            data["energy"]["scalars"]["maximum_temperature_c"] = 25.
            data["energy"]["units"]["maximum_temperature_c"] = "C"
        _change_bundle_metadata(plan, index, add_temperature)
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    with pytest.raises(ValueError, match="additive"):
        results.portfolio_total("maximum_temperature_c", case_ids=[0, 1])
    _change_bundle_metadata(plan, 1, lambda data: data["weather"].update(calendar_year=2024))
    changed = StudyResults.collect(spec, plan, tmp_path / "archive-2")
    with pytest.raises(ValueError, match="calendar|boundaries"):
        changed.portfolio_total("space_heating_demand_kwh", case_ids=[0, 1])


def test_producer_rejected_heating_is_not_used_for_energy_summaries(tmp_path):
    spec, plan = prepared(tmp_path)
    path = plan / "results/000000.json"
    row = json.loads(path.read_text())
    row["result"]["coverage"] = {"ready": False, "thermal_complete": False,
        "delivery_complete": False, "lca_complete": True,
        "diagnostics": [{"code": "annual_reconciliation", "field": "space_heating_demand_kwh", "severity": "error"}]}
    from epsm_workflows.records import digest
    row.pop("record_sha256")
    row["record_sha256"] = digest(row)
    path.write_text(json.dumps(row))
    (plan / "attempts/000000" / f"{row['id']}.json").write_text(json.dumps(row))
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    with pytest.raises(ValueError, match="coverage"):
        result.aggregate_energy(0)
    assert result.difference(0, 0, "space_heating_demand_kwh")["difference"] is None
    assert result.portfolio_total("space_heating_demand_kwh", case_ids=[0])["value"] is None
    assert result.hourly(0).tolist() == [1., 2., 3., 4.]


def test_archive_completion_marker_cannot_be_a_symbolic_link(tmp_path):
    spec, plan = prepared(tmp_path)
    archive = tmp_path / "archive"
    StudyResults.collect(spec, plan, archive)
    header = archive / "manifest.json"
    outside = tmp_path / "manifest.json"
    shutil.move(header, outside)
    header.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        StudyResults.open(archive)


def test_unrecognized_special_files_are_not_silently_dropped(tmp_path):
    import os
    if not hasattr(os, "mkfifo"):
        pytest.skip("POSIX file-type check")
    spec, plan = prepared(tmp_path)
    os.mkfifo(plan / "artifacts" / "unfinished-pipe")
    with pytest.raises(ValueError, match="regular files"):
        StudyResults.collect(spec, plan, tmp_path / "archive")
    assert not (tmp_path / "archive").exists()


def test_index_cannot_claim_completeness_for_missing_outputs(tmp_path):
    spec, plan = prepared(tmp_path)
    archive = tmp_path / "archive"
    StudyResults.collect(spec, plan, archive)
    header = archive / "manifest.json"
    value = json.loads(header.read_text())
    value["entries"][0]["result_complete"] = True
    value["entries"][0]["outputs"]["space_heating_demand_kwh"]["available"] = False
    from epsm_studies._records import digest
    value.pop("id")
    value["id"] = digest(value)
    header.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="completeness"):
        StudyResults.open(archive)


def test_collected_result_engine_must_match_its_declared_case(tmp_path):
    spec, plan = prepared(tmp_path)
    _change_bundle_metadata(plan, 0, lambda data: data.update(engine="energyplus"))
    with pytest.raises(ValueError, match="engine.*frozen case"):
        StudyResults.collect(spec, plan, tmp_path / "archive")


def test_descriptive_helpers_expose_missing_cases_and_compatible_boundaries(tmp_path):
    spec, plan = prepared(tmp_path, partial=True, annual=True)
    result = StudyResults.collect(spec, plan, tmp_path / "archive")
    summary = result.describe("space_heating_demand_kwh", case_ids=[0, 1, 2, 3])
    assert summary["count"] == 4 and summary["available"] == 2 and summary["missing"] == 2
    assert summary["min"] == summary["max"] == summary["mean"] == 8760.
    assert summary["complete"] is False
    assert result.describe("space_heating_demand_kwh", case_ids=[0])["complete"] is True
    _change_bundle_metadata(plan, 1, lambda data: data["energy"].update(boundary="different-delivery-boundary"))
    changed = StudyResults.collect(spec, plan, tmp_path / "archive-2")
    with pytest.raises(ValueError, match="boundaries"):
        changed.describe("space_heating_demand_kwh", case_ids=[0, 1])


def test_owner_acceptance_cannot_hide_a_signal_omitted_from_the_saved_bundle(tmp_path):
    spec, plan = prepared(tmp_path, annual=True)
    row = json.loads((plan / "results/000000.json").read_text())
    bundle = plan / row["result"]["path"]
    _change_bundle_metadata(plan, 0, lambda data: data["energy"].update(hourly_signals=[]))
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["arrays"]["hourly"] = {}
    path.write_text(json.dumps(manifest))
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    assert results.coverage()["complete"] is False
    assert results.coverage()["outputs"]["space_heating_demand_kwh"]["missing"] == 1
    with pytest.raises(KeyError, match="not retained"):
        results.hourly(0)


def test_receipt_coverage_flags_must_be_booleans(tmp_path):
    spec, plan = prepared(tmp_path, annual=True)
    path = plan / "results/000000.json"
    row = json.loads(path.read_text())
    row["result"]["coverage"]["thermal_complete"] = "false"
    from epsm_workflows.records import digest
    row.pop("record_sha256")
    row["record_sha256"] = digest(row)
    path.write_text(json.dumps(row))
    (plan / "attempts/000000" / f"{row['id']}.json").write_text(json.dumps(row))
    with pytest.raises(ValueError, match="coverage.*boolean"):
        StudyResults.collect(spec, plan, tmp_path / "archive")


def test_invalid_archive_header_has_a_public_validation_error(tmp_path):
    (tmp_path / "manifest.json").write_text("[]")
    with pytest.raises(ValueError, match="mapping"):
        StudyResults.open(tmp_path)


def test_nonfinite_legacy_array_is_rejected_when_explicitly_read(tmp_path):
    spec, plan = prepared(tmp_path)
    row = json.loads((plan / "results/000000.json").read_text())
    bundle = plan / row["result"]["path"]
    path = bundle / "arrays/heating.npy"
    np.save(path, [float("nan"), 2., 3., 4.], allow_pickle=False)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["arrays"]["hourly"]["space_heating_demand_kwh"]["sha256"] = _sha(path)
    manifest_path.write_text(json.dumps(manifest))
    results = StudyResults.collect(spec, plan, tmp_path / "archive")
    assert results.coverage()["complete"] is False
    with pytest.raises(ValueError, match="nonfinite"):
        results.hourly(0)
