# SPDX-License-Identifier: MIT
"""Portable study outcome indexes with explicit, lazy access to owner result data."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import csv
import json
import math
from datetime import datetime, timedelta
from io import StringIO
import os
from pathlib import Path
import shutil
import tempfile

from ._logging import context_logger, operation
from ._records import canonical, checksum, digest, publish_json, read_json, relative_path, short
from .spec import StudySpec


_BUNDLE = "epsm-evaluation-bundle/1"
_REFERENCE = "epsm-evaluation-reference/1"
_FORMAT = "epsm-study-results/1"


def _checked_ref(root, reference, *, verify=True):
    if not isinstance(reference, Mapping) or not isinstance(reference.get("sha256"), str):
        raise ValueError("Artifact reference needs a path and checksum")
    path = relative_path(root, reference.get("path"))
    if verify and (not path.is_file() or checksum(path) != reference["sha256"]):
        raise ValueError(f"Missing or changed artifact checksum: {reference.get('path')}")
    return path


def _bundle(root, *, verify_arrays=False):
    manifest = read_json(root / "manifest.json")
    if manifest.get("format") != _BUNDLE:
        raise ValueError("Unsupported evaluation bundle format")
    metadata_path = _checked_ref(root, manifest.get("metadata"))
    metadata = read_json(metadata_path)
    if not isinstance(metadata, Mapping):
        raise ValueError("Evaluation metadata must be a mapping")
    if metadata.get("id") != manifest.get("evaluation_id"):
        raise ValueError("Evaluation bundle identity differs from metadata")
    arrays = manifest.get("arrays", {})
    if not isinstance(arrays, Mapping) or not isinstance(arrays.get("hourly"), Mapping):
        raise ValueError("Evaluation bundle needs named hourly array references")
    if set(arrays["hourly"]) != set(metadata.get("energy", {}).get("hourly_signals", [])):
        raise ValueError("Evaluation hourly signal index differs from metadata")
    references = [*arrays["hourly"].values()]
    if arrays.get("time_axis") is not None:
        references.append(arrays["time_axis"])
    references.extend(manifest.get("artifacts", {}).values())
    references.extend(manifest.get("inputs", {}).values())
    for reference in references:
        _checked_ref(root, reference, verify=verify_arrays)
    return manifest, metadata


def _outputs(spec):
    return spec.workflow.get("outputs", [])


def _coverage(metadata, manifest, outputs):
    """Describe saved producer output availability, without recalculating physics."""
    energy, lca = metadata.get("energy", {}), metadata.get("lca", {})
    available = {}
    for output in outputs:
        request = {"name": output} if isinstance(output, str) else output
        name = request["name"]
        unit = request.get("unit")
        if name == "lca":
            ok = lca.get("status") == "complete"
        elif name == "delivered_energy":
            ok = bool(energy.get("annual") and not energy.get("requirements")
                      and energy.get("delivered_by_carrier") is not None
                      and energy.get("diagnostics", {}).get("accepted") is True)
        elif request.get("resolution") == "hourly":
            hourly = manifest.get("arrays", {}).get("hourly", {}) if manifest else {}
            axis = manifest.get("arrays", {}).get("time_axis", {}) if manifest else {}
            if manifest:
                shape = hourly.get(name, {}).get("shape")
                ok = bool(shape and shape == axis.get("shape") and len(shape) == 1 and shape[0] > 0)
            else:
                values = energy.get("hourly", {}).get(name)
                axis_values = energy.get("time_axis", [])
                ok = isinstance(values, list) and bool(values) and len(values) == len(axis_values)
            ok = bool(ok and energy.get("diagnostics", {}).get("accepted") is True)
            if request.get("annual"):
                ok = ok and energy.get("annual") is True
        else:
            ok = name in energy.get("scalars", {}) and energy["scalars"][name] is not None
        if unit and name not in {"lca", "delivered_energy"}:
            ok = ok and energy.get("units", {}).get(name) == unit
        available[name] = {"required": request.get("required", True), "available": bool(ok)}
    return available


def _entry(index, case, row, execution_root, outputs):
    axes = case.get("inputs", {}).get("axes", {})
    entry = {"index": index, "case_id": case["id"], "name": case.get("name", ""),
             "axes": axes, "status": row["status"] if row else "not_run",
             "attempt_id": row["id"] if row else None, "evaluation_id": None,
             "energy_accepted": None, "lca_status": "not_run", "metrics": {},
             "outputs": {}, "result_complete": False,
             "error": {key: value for key, value in (row or {}).get("error", {}).items()
                       if key in {"code", "type", "message"}}}
    if not row or row["status"] != "succeeded":
        entry["outputs"] = {o if isinstance(o, str) else o["name"]:
                            {"required": True if isinstance(o, str) else o.get("required", True), "available": False}
                            for o in outputs}
        return entry
    result = row["result"]
    if result.get("format") == _REFERENCE:
        bundle_path = relative_path(execution_root, result.get("path"))
        if result.get("manifest_sha256") is not None and checksum(bundle_path / "manifest.json") != result["manifest_sha256"]:
            raise ValueError("Changed evaluation bundle manifest checksum")
        manifest, metadata = _bundle(bundle_path, verify_arrays=True)
        if result.get("evaluation_id") is not None and result["evaluation_id"] != metadata["id"]:
            raise ValueError("Evaluation reference identity differs from its bundle")
        entry["bundle"] = str(Path("execution") / result["path"])
    elif "energy" in result and "lca" in result:
        # Old prepared outcomes remain inspectable. The new reference route avoids
        # their large embedded arrays; opening an archive still uses only the index.
        manifest, metadata = None, result
        entry["inline"] = f"execution/results/{index:06d}.json"
    else:
        raise ValueError("Successful case does not contain a supported EPSM evaluation")
    energy, lca = metadata.get("energy", {}), metadata.get("lca", {})
    entry.update(evaluation_id=metadata.get("id"), energy_accepted=energy.get("diagnostics", {}).get("accepted"),
                 lca_status=lca.get("status", "unrecorded"))
    entry["metrics"] = {**energy.get("scalars", {}), **{key: lca.get(key) for key in (
        "material_gwp_kgco2e", "operational_gwp_kgco2e", "total_gwp_kgco2e")}}
    entry["outputs"] = _coverage(metadata, manifest, outputs)
    producer_coverage = result.get("coverage")
    if producer_coverage is not None:
        entry["producer_coverage"] = producer_coverage
        for name, coverage in entry["outputs"].items():
            if name == "lca":
                coverage["available"] = bool(producer_coverage.get("lca_complete"))
            elif name == "delivered_energy":
                coverage["available"] = bool(producer_coverage.get("delivery_complete"))
            elif name == "space_heating_demand_kwh":
                coverage["available"] = bool(producer_coverage.get("thermal_complete"))
            else:
                issues = [issue for issue in producer_coverage.get("diagnostics", [])
                          if issue.get("field") in {name, "energy.time_axis", "energy.diagnostics"}]
                coverage["available"] = coverage["available"] and not issues
    entry["result_complete"] = bool(entry["energy_accepted"] is True and all(
        not value["required"] or value["available"] for value in entry["outputs"].values())
        and (producer_coverage is None or producer_coverage.get("ready") is True))
    return entry


def _copy_tree(source, destination):
    if source.is_symlink():
        raise ValueError("Execution evidence must not contain symlinks")
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in sorted(source.iterdir()):
            _copy_tree(child, destination / child.name)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


class StudyResults:
    """Immutable archive index with every planned case and retained attempt.

    ``open`` reads only the small completion manifest. ``table``, ``select``,
    ``coverage``, ``summary`` and printed representations inspect loaded metadata.
    Explicit ``hourly`` and ``time_axis`` calls verify and load only the requested
    NumPy file; install ``epsm_studies[results]`` for those operations. No engine,
    Workflows or EPSM import is needed to reopen or inspect an archive.
    """
    def __init__(self, directory, manifest):
        self.directory = Path(directory).resolve()
        self._json = canonical(manifest)
        self.spec = StudySpec.from_dict(manifest["study"])

    @property
    def id(self):
        return json.loads(self._json)["id"]

    @property
    def plan_id(self):
        return json.loads(self._json)["plan_id"]

    @classmethod
    @operation("study.results.open")
    def open(cls, directory):
        """Read a completed archive index; full file verification is explicit."""
        root = Path(directory)
        if not (root / "manifest.json").is_file():
            raise ValueError("Directory is not a completed study result archive")
        value = read_json(root / "manifest.json")
        if value.get("format") != _FORMAT:
            raise ValueError("Unsupported study result archive format")
        identity = value.get("id")
        if identity != digest({k: v for k, v in value.items() if k != "id"}):
            raise ValueError("Study result archive identity differs from its content")
        if not isinstance(value.get("entries"), list) or not isinstance(value.get("files"), dict):
            raise ValueError("Study archive needs case entries and a file inventory")
        case_ids = [entry["case_id"] for entry in value["entries"]]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Study archive has duplicate case identities")
        return cls(root, value)

    @classmethod
    @operation("study.results.collect")
    def collect(cls, study: StudySpec, execution_directory, directory):
        """Publish a verified, portable snapshot without changing execution evidence.

        Collection requires Workflows and copies prepared inputs, attempts,
        selected outcomes, artifacts and logs. Caches/locks are excluded. Source
        outcomes must stay unchanged during collection. An existing identical
        snapshot is reused; a different snapshot requires another directory.
        The final manifest is published last as the completion marker. A failed
        publication never replaces an existing archive.
        """
        if hasattr(study, "spec"):
            study = study.spec
        if not isinstance(study, StudySpec):
            raise TypeError("Pass a StudySpec or Study")
        try:
            from epsm_workflows.execution import validate_plan, read_results, read_attempts
        except ImportError as error:
            raise ImportError("Install current epsm_studies[workflows] to collect execution outcomes") from error
        source, target = Path(execution_directory).resolve(), Path(directory).resolve()
        if target.is_relative_to(source) or source.is_relative_to(target):
            raise ValueError("Archive and execution directories must be separate")
        validated = validate_plan(source)
        plan = validated.get("manifest", validated)
        expected_workflow = plan.get("environment", {}).get("workflow_id")
        if expected_workflow is not None and expected_workflow != digest(study.workflow):
            raise ValueError("Study workflow differs from the frozen execution plan")
        if (source / "workflow.json").exists() and read_json(source / "workflow.json") != study.workflow:
            raise ValueError("Study workflow differs from the retained workflow specification")
        rows = read_results(source, require_success=False)
        attempts = read_attempts(source)
        observations = list(rows)
        for index, row in enumerate(observations):
            if row is None:
                running = [attempt for attempt in attempts if attempt["index"] == index and attempt["status"] == "running"]
                observations[index] = running[-1] if running else None
        entries = [_entry(index, read_json(source / "cases" / f"{index:06d}.json"), row,
                          source, _outputs(study)) for index, row in enumerate(observations)]
        if any(row is not None and row not in attempts for row in rows):
            raise ValueError("Selected outcome has no matching retained attempt")
        for attempt in attempts:
            result = attempt.get("result", {})
            if result.get("format") == _REFERENCE:
                _bundle(relative_path(source, result.get("path")), verify_arrays=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{target.name}.", dir=target.parent) as temporary:
            staging = Path(temporary)
            execution = staging / "execution"
            execution.mkdir()
            _copy_tree(source / "manifest.json", execution / "manifest.json")
            for name in ("workflow.json", "control.json", "cases", "assets", "attempts", "results", "artifacts", "logs"):
                if (source / name).exists():
                    _copy_tree(source / name, execution / name)
            if read_results(source, require_success=False) != rows or read_attempts(source) != attempts:
                raise ValueError("Execution outcomes changed during archive collection; collect again")
            validate_plan(execution)
            if read_results(execution, require_success=False) != rows or read_attempts(execution) != attempts:
                raise ValueError("Copied execution evidence differs from the selected snapshot")
            # Verify the copied selected bundles before publishing their index.
            for entry in entries:
                if "bundle" in entry:
                    _bundle(relative_path(staging, entry["bundle"]), verify_arrays=True)
            files = {str(path.relative_to(staging)): checksum(path)
                     for path in sorted(staging.rglob("*")) if path.is_file()}
            value = {"format": _FORMAT, "study": study.to_dict(), "plan_id": plan["id"],
                     "entries": entries, "attempts": attempts, "files": files}
            value["id"] = digest(value)
            if target.exists():
                existing = cls.open(target)
                if existing.id == value["id"]:
                    existing.verify()
                    return existing
                raise FileExistsError("Archive exists with different outcomes; choose a new directory")
            # Exclusive mkdir prevents replacing a concurrent writer's archive.
            # Readers reject a directory until the completion manifest exists.
            target.mkdir()
            try:
                for child in staging.iterdir():
                    shutil.move(str(child), target / child.name)
                publish_json(target / "manifest.json", value)
            except BaseException:
                shutil.rmtree(target)
                raise
        context_logger(__name__).info("Published study result archive", extra={
            "epsm_event": "study.results.saved", "epsm_context": {"study_id": study.id},
            "epsm_details": {"archive_id": value["id"], "cases": len(entries), "directory": str(target)}})
        return cls(target, value)

    def table(self):
        """Return independent metadata rows; does not read arrays or artifacts."""
        return json.loads(self._json)["entries"]

    def select(self, **selectors):
        """Select index rows by exact entry/axis fields, without loading results."""
        return tuple(entry for entry in self.table() if all(
            entry.get(key, entry["axes"].get(key)) == value for key, value in selectors.items()))

    def _entry(self, case):
        rows = self.table()
        if isinstance(case, int) and not isinstance(case, bool):
            if not 0 <= case < len(rows):
                raise IndexError(case)
            return rows[case]
        for entry in rows:
            if entry["case_id"] == case:
                return entry
        raise KeyError(f"Unknown prepared case: {case}")

    def coverage(self):
        """Count execution outcomes and required output coverage without array I/O."""
        rows = self.table()
        counts = Counter(row["status"] for row in rows)
        outputs = {}
        for row in rows:
            for name, coverage in row["outputs"].items():
                current = outputs.setdefault(name, {"available": 0, "missing": 0, "required": coverage["required"]})
                current["available" if coverage["available"] else "missing"] += 1
        return {"total": len(rows), "succeeded": counts["succeeded"], "failed": counts["failed"],
                "not_run": counts["not_run"], "running": counts["running"],
                "complete_results": sum(row["result_complete"] for row in rows),
                "complete": bool(rows) and all(row["result_complete"] for row in rows), "outputs": outputs}

    def attempts(self, case=None):
        """Return retained Workflows attempt evidence, optionally for one case."""
        attempts = json.loads(self._json)["attempts"]
        if case is not None:
            case_id = self._entry(case)["case_id"]
            attempts = [attempt for attempt in attempts if attempt["case_id"] == case_id]
        return tuple(attempts)

    def _evaluation(self, case):
        entry = self._entry(case)
        if entry["status"] != "succeeded":
            raise ValueError("Case has no successful evaluation; inspect its attempt evidence")
        if "bundle" in entry:
            root = relative_path(self.directory, entry["bundle"])
            manifest, metadata = _bundle(root)
            return root, manifest, metadata
        path = relative_path(self.directory, entry["inline"])
        expected = json.loads(self._json)["files"].get(entry["inline"])
        if checksum(path) != expected:
            raise ValueError("Changed inline evaluation checksum")
        return None, None, read_json(path)["result"]

    def evaluation_metadata(self, case):
        """Explicitly read one evaluation's owner metadata and its assessment evidence."""
        return self._evaluation(case)[2]

    @staticmethod
    def _array(root, reference):
        path = _checked_ref(root, reference)
        try:
            import numpy as np
        except ImportError as error:
            raise ImportError("Install epsm_studies[results] to read numerical arrays") from error
        array = np.load(path, allow_pickle=False)
        if array.ndim != 1 or array.dtype.kind not in "biufUS":
            raise ValueError("Saved arrays must be one-dimensional numeric or calendar data")
        if array.dtype.kind in "biuf" and not np.isfinite(array).all():
            raise ValueError("Saved result array contains nonfinite values")
        if list(array.shape) != reference.get("shape") or array.dtype != np.dtype(reference.get("dtype")):
            raise ValueError("Saved array shape or dtype differs from its manifest")
        return array

    def hourly(self, case, signal="space_heating_demand_kwh"):
        """Verify and load one saved signal with its original units; no simulation."""
        root, manifest, metadata = self._evaluation(case)
        if manifest:
            try:
                reference = manifest["arrays"]["hourly"][signal]
            except KeyError:
                raise KeyError(f"Hourly signal was not retained: {signal}") from None
            return self._array(root, reference)
        import numpy as np
        return np.asarray(metadata["energy"]["hourly"][signal])

    def time_axis(self, case):
        """Verify and load one result's recorded local-standard-time calendar."""
        root, manifest, metadata = self._evaluation(case)
        if manifest:
            return self._array(root, manifest["arrays"]["time_axis"])
        import numpy as np
        return np.asarray(metadata["energy"]["time_axis"])

    @operation("study.results.verify")
    def verify(self):
        """Explicitly checksum every retained file, without importing an engine."""
        for name, expected in json.loads(self._json)["files"].items():
            path = relative_path(self.directory, name)
            if not path.is_file() or checksum(path) != expected:
                raise ValueError(f"Missing or changed archive artifact checksum: {name}")
        return {"id": self.id, "verified_files": len(json.loads(self._json)["files"])}

    def aggregate_energy(self, case, signal="space_heating_demand_kwh", *, period="monthly"):
        """Sum a retained kWh signal by recorded month/year; never average calendars.

        The calendar must be nonempty, continuous and hourly, and every value
        finite. This operation loads one signal and its time axis explicitly.
        It does not fill missing hours or convert temperature/power signals.
        """
        if period not in {"monthly", "annual"}:
            raise ValueError("Energy aggregation period must be monthly or annual")
        metadata = self.evaluation_metadata(case)
        if metadata["energy"].get("units", {}).get(signal) != "kWh":
            raise ValueError("Temporal energy aggregation requires a kWh signal")
        values = self.hourly(case, signal)
        axis = self.time_axis(case)
        stamps = [datetime.fromisoformat(str(value)) for value in axis]
        if not stamps or len(stamps) != len(values) or any(
                b - a != timedelta(hours=1) for a, b in zip(stamps, stamps[1:])):
            raise ValueError("Energy aggregation requires a complete continuous hourly calendar")
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Energy aggregation requires finite hourly values")
        groups = {}
        for stamp, value in zip(stamps, values):
            key = stamp.strftime("%Y-%m" if period == "monthly" else "%Y")
            groups.setdefault(key, []).append(float(value))
        return {key: math.fsum(items) for key, items in groups.items()}

    def _metric(self, case, metric):
        entry = self._entry(case)
        if entry["status"] != "succeeded":
            return None, None, None
        metadata = self.evaluation_metadata(case)
        impacts = {"material_gwp_kgco2e", "operational_gwp_kgco2e", "total_gwp_kgco2e"}
        if metric in impacts:
            assessment = metadata.get("lca", {})
            value = assessment.get(metric)
            basis = {"assessment": assessment.get("assessment")}
            unit = "kg CO2e"
        else:
            energy = metadata.get("energy", {})
            value = energy.get("scalars", {}).get(metric)
            unit = energy.get("units", {}).get(metric)
            basis = {"energy_boundary": energy.get("boundary")}
            if metric.endswith("_m2"):
                raise ValueError("Portfolio helpers require absolute metrics, not area-normalized values")
            if energy.get("diagnostics", {}).get("accepted") is not True:
                value = None
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("Summary metrics must be finite numbers or explicit unknown values")
        return value, unit, basis

    def portfolio_total(self, metric, *, case_ids):
        """Sum explicitly selected independent subjects with visible missing coverage.

        Select one case per subject and one engine/sample/scenario combination.
        Different per-subject weather files are allowed. Units and assessment or
        energy boundaries must agree. A missing result gives ``value=None``;
        ``known_subtotal`` describes only the available selected subjects.
        """
        cases = list(case_ids)
        if not cases or len({self._entry(case)["case_id"] for case in cases}) != len(cases):
            raise ValueError("Select nonempty, distinct cases for a portfolio total")
        entries = [self._entry(case) for case in cases]
        subjects = [entry["axes"].get("subject_id", entry["axes"].get("building_id")) for entry in entries]
        if any(subject is None for subject in subjects) or len(set(subjects)) != len(subjects):
            raise ValueError("Select exactly one identified case per portfolio subject")
        for dimension in ("engine", "sample_id", "scenario_id"):
            selected = {entry["axes"].get(dimension) for entry in entries}
            if len(selected) > 1:
                raise ValueError(f"Portfolio total cannot mix {dimension} choices")
        values = [self._metric(case, metric) for case in cases]
        known = [item for item in values if item[0] is not None]
        if known and (None in {item[1] for item in known} or
                      len({(item[1], canonical(item[2])) for item in known}) != 1):
            raise ValueError("Portfolio metrics have incompatible or missing units/reference boundaries")
        if known and metric.endswith("kgco2e") and known[0][2]["assessment"] is None:
            raise ValueError("Impact totals require recorded assessment boundaries")
        complete = len(known) == len(cases)
        subtotal = math.fsum(item[0] for item in known) if known else None
        return {"metric": metric, "value": subtotal if complete else None,
                "known_subtotal": subtotal, "unit": known[0][1] if known else None,
                "selected": len(cases), "available": len(known), "complete": complete,
                "case_ids": [entry["case_id"] for entry in entries]}

    def difference(self, reference, candidate, metric):
        """Describe candidate minus baseline for one subject and engine.

        Physical states may differ. This helper does not infer attribution,
        thresholds or causal interpretation. Use ``compare_engines`` for the
        stricter identical-input comparison between different engines.
        """
        rows = [self._entry(case) for case in (reference, candidate)]
        subjects = [row["axes"].get("subject_id", row["axes"].get("building_id")) for row in rows]
        if None in subjects or subjects[0] != subjects[1]:
            raise ValueError("Baseline differences require the same subject")
        if rows[0]["axes"].get("engine") != rows[1]["axes"].get("engine"):
            raise ValueError("Use compare_engines for results from different engines")
        ref, cand = [self._metric(case, metric) for case in (reference, candidate)]
        if ref[0] is not None and cand[0] is not None and (ref[1] is None or ref[1:] != cand[1:]):
            raise ValueError("Difference metrics have incompatible units/reference boundaries")
        complete = ref[0] is not None and cand[0] is not None
        delta = cand[0] - ref[0] if complete else None
        return {"metric": metric, "reference": ref[0], "candidate": cand[0],
                "difference": delta,
                "difference_percent": 100 * delta / ref[0] if complete and ref[0] else None,
                "unit": ref[1] or cand[1], "complete": complete,
                "reference_case_id": rows[0]["case_id"], "candidate_case_id": rows[1]["case_id"]}

    def compare_engines(self, reference, candidate, *, expected_time_axis,
                        signal="space_heating_demand_kwh"):
        """Apply the existing strict engine comparator to two retained evaluations.

        Supply the intended calendar independently of observed result coverage.
        Shared physical, snapshot and weather identities are required. Only the
        requested signal is loaded; no engine or scientific calculation runs.
        """
        from types import SimpleNamespace
        from .comparison import compare_energy_results
        results, identities = [], []
        for case in (reference, candidate):
            metadata = self.evaluation_metadata(case)
            energy = metadata["energy"]
            if not energy.get("run_id"):
                raise ValueError("Engine comparison requires a retained raw engine run identity")
            results.append(SimpleNamespace(run_id=energy["run_id"], scalars=energy["scalars"],
                hourly={signal: self.hourly(case, signal)}, units=energy["units"],
                diagnostics=energy["diagnostics"], time_axis=self.time_axis(case)))
            identities.append({"building_snapshot_sha256": metadata.get("state_id"),
                "physical_inputs_sha256": energy["diagnostics"].get("physical_inputs_sha256"),
                "weather_sha256": metadata.get("weather", {}).get("weather_sha256", metadata.get("weather", {}).get("sha256"))})
        return compare_energy_results(*results, reference_identity=identities[0],
            candidate_identity=identities[1], expected_time_axis=expected_time_axis, signal=signal)

    @operation("study.results.export")
    def export(self, path, *, format=None, **selectors):
        """Publish an independent CSV/JSON metadata table, refusing overwrite.

        Rows include failed and unrun cases unless explicitly filtered. CSV
        flattens axes and scalar metrics; JSON retains the complete index rows.
        No hourly arrays are read. Use a separate path for another export.
        """
        path = Path(path)
        format = format or path.suffix.lstrip(".")
        rows = list(self.select(**selectors))
        if format == "json":
            return publish_json(path, {"format": "epsm-study-table/1", "archive_id": self.id, "rows": rows})
        if format != "csv":
            raise ValueError("Study table export format must be csv or json")
        records = []
        for row in rows:
            records.append({**{key: row[key] for key in ("index", "case_id", "name", "status", "attempt_id",
                         "evaluation_id", "energy_accepted", "lca_status", "result_complete")},
                            **row["axes"], **row["metrics"]})
        fields = list(dict.fromkeys(key for row in records for key in row))
        if not fields:
            fields = ["case_id", "status"]
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
                output.write(stream.getvalue())
                output.flush()
                os.fsync(output.fileno())
            os.link(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return path

    def summary(self):
        return {"id": self.id, "study_id": self.spec.id, "plan_id": self.plan_id,
                "name": self.spec.name, **self.coverage()}

    def __repr__(self):
        coverage = self.coverage()
        return f"StudyResults(name={short(self.spec.name)}, cases={coverage['total']}, complete={coverage['complete']}, id='{self.id[:12]}')"

    __str__ = __repr__
