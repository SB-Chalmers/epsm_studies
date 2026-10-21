"""A study can be retained and inspected without its execution environment."""
import copy
import json
import subprocess
import sys
import types

import pytest

from epsm_studies import Study, StudySpec


WORKFLOW = {
    "format": "epsm-workflow/1",
    "sampling": {"method": "lhs", "count": 4, "seed": 17},
    "outputs": [{"name": "space_heating_demand_kwh", "required": True}],
}


def test_study_spec_roundtrip_preserves_owner_workflow_and_copies():
    workflow = copy.deepcopy(WORKFLOW)
    spec = StudySpec("Envelope alternatives", question="What changes heating?", workflow=workflow,
                     metadata={"tags": ["pilot"]}, protocol={"assumptions": ["fixed weather"]},
                     reporting={"metrics": ["space_heating_demand_kwh"]})
    identity = spec.id
    workflow["sampling"]["seed"] = 99
    spec.workflow["sampling"]["seed"] = 88
    spec.metadata["tags"].append("changed")
    assert spec.workflow == WORKFLOW
    assert spec.metadata["tags"] == ["pilot"]
    assert StudySpec.from_dict(spec.to_dict()).id == identity
    changed = spec.to_dict()
    changed["workflow"]["sampling"]["count"] = 5
    with pytest.raises(ValueError, match="identity"):
        StudySpec.from_dict(changed)
    assert "Envelope alternatives" in repr(spec)
    assert len(repr(spec)) <= 160


@pytest.mark.parametrize("change", [
    lambda x: x.update(format="epsm-study-spec/99"),
    lambda x: x.update(reporting={"value": float("nan")}),
    lambda x: x.update(workflow={"sampling": {}}),
    lambda x: x.update(unexpected=True),
])
def test_study_spec_rejects_bad_stored_data(change):
    data = StudySpec("Pilot", workflow=WORKFLOW).to_dict()
    data.pop("id")
    change(data)
    with pytest.raises((TypeError, ValueError)):
        StudySpec.from_dict(data)


def test_study_save_and_open_do_not_require_execution_packages(tmp_path):
    study = Study(StudySpec("Offline", workflow=WORKFLOW))
    path = study.save(tmp_path / "study.json")
    study.save(path)
    assert Study.open(path).spec.id == study.spec.id
    with pytest.raises(FileExistsError):
        Study(StudySpec("Other", workflow=WORKFLOW)).save(path)
    script = r'''
import importlib.abc, json, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'epsm', 'epsm_workflows', 'epsm_core', 'epsm_rc', 'numpy'}:
            raise RuntimeError('Unexpected execution import: ' + fullname)
sys.meta_path.insert(0, Block())
from epsm_studies import Study
study = Study.open(sys.argv[1])
assert study.spec.name == 'Offline'
assert '$defs' not in study.spec.schema()
assert study.to_dict()['workflow']['sampling']['count'] == 4
print(study)
'''
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_facade_delegates_edits_and_keeps_earlier_revisions(monkeypatch, tmp_path):
    class OwnerWorkflow:
        def __init__(self, data):
            self.data = copy.deepcopy(data)
        @classmethod
        def from_dict(cls, data):
            return cls(data)
        @classmethod
        def template(cls, **options):
            return cls({"format": "epsm-workflow/1", "options": options})
        def to_dict(self):
            return copy.deepcopy(self.data)
        def set(self, key, value):
            self.data[key] = value
            return self
        def vary(self, key, **options):
            self.data.setdefault("parameters", {})[key] = options
            return self
        def preview(self):
            return {"cases": self.data.get("count", 0)}
        def prepare(self, directory):
            return {"id": "frozen-plan", "data": self.to_dict()}
    monkeypatch.setitem(sys.modules, "epsm_workflows", types.SimpleNamespace(WorkflowSpec=OwnerWorkflow))
    study = Study("Pilot", samples=3, seed=4, engines=["epsm_rc"])
    old = study.spec
    assert study.set("count", 3).vary("geometry.wwr", min=.1, max=.5) is study
    frozen = study.prepare(tmp_path / "plan")
    study.set("count", 5)
    assert old.id != study.spec.id
    assert frozen["data"]["count"] == 3
    assert study.preview() == {"cases": 5}
    assert study.spec.workflow["engines"] == ["epsm_rc"]


def test_study_json_rejects_duplicate_fields_and_preserves_existing_file(tmp_path):
    path = tmp_path / "study.json"
    path.write_text('{"format":"epsm-study-spec/1","format":"other"}')
    with pytest.raises(ValueError, match="Duplicate"):
        Study.open(path)
    assert path.read_text().endswith('"other"}')


def test_run_honors_frozen_worker_and_executor_choices(monkeypatch, tmp_path):
    pytest.importorskip("epsm_workflows", reason="Optional execution integration")
    from epsm_workflows import VeraExecutor
    import epsm_workflows
    from epsm_studies._records import digest
    workflow = {**WORKFLOW, "execution": {"executor": "local", "workers": 3}}
    (tmp_path / "workflow.json").write_text(json.dumps(workflow))
    calls = []
    monkeypatch.setattr(epsm_workflows, "validate_plan", lambda path: {"environment": {"workflow_id": digest(workflow)}})
    monkeypatch.setattr(epsm_workflows, "run_local", lambda path, **kw: calls.append((path, kw)) or {"succeeded": 1})
    study = Study(StudySpec("Run", workflow=WORKFLOW))
    assert study.run(tmp_path) == {"succeeded": 1}
    assert calls[-1][1]["workers"] == 3
    workflow["execution"]["executor"] = "vera"
    (tmp_path / "workflow.json").write_text(json.dumps(workflow))
    with pytest.raises(ValueError, match="VeraExecutor"):
        study.run(tmp_path)
    executor = VeraExecutor("vera.example", "/campaign")
    monkeypatch.setattr(VeraExecutor, "stage", lambda self, path: calls.append("stage"))
    monkeypatch.setattr(VeraExecutor, "submit", lambda self, path, **kw: calls.append(kw) or {"job_id": "123"})
    assert study.run(tmp_path, executor=executor, submit_options={"partition": "test"}) == {"job_id": "123"}
    assert calls[-2:] == ["stage", {"partition": "test"}]


def test_portable_sections_reject_silent_key_coercion_and_overflow(tmp_path):
    with pytest.raises(TypeError, match="keys must be strings"):
        StudySpec("Bad keys", workflow=WORKFLOW, metadata={1: "would be silently renamed"})
    path = tmp_path / "bad.json"
    path.write_text('{"number":1e10000}')
    with pytest.raises(ValueError, match="Nonfinite"):
        Study.open(path)


def test_composed_schema_covers_the_single_study_document_and_owner_references():
    import jsonschema
    pytest.importorskip("epsm_workflows")
    study = Study("Schema", samples=3, seed=4)
    schema = study.schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(study.to_dict())
    malformed = study.to_dict()
    malformed["format"] = "unknown"
    assert not validator.is_valid(malformed)
    malformed = study.to_dict()
    malformed["workflow"]["sampling"]["samples"] = 0
    assert not validator.is_valid(malformed)
    malformed = study.to_dict()
    malformed["metadata"]["name"] = "   "
    assert not validator.is_valid(malformed)
    # A schema request must not mutate the reusable owner schema or its refs.
    from epsm_workflows import WorkflowSpec
    assert WorkflowSpec.schema()["properties"]["sampling"]["$ref"].startswith("#/$defs/")


def test_study_spec_schema_is_dependency_light_and_uses_the_envelope_rules():
    import jsonschema
    schema = StudySpec.schema()
    jsonschema.Draft202012Validator(schema).validate(StudySpec("Portable", workflow=WORKFLOW).to_dict())
    malformed = StudySpec("Portable", workflow=WORKFLOW).to_dict()
    malformed.pop("metadata")
    assert not jsonschema.Draft202012Validator(schema).is_valid(malformed)
    with pytest.raises(ValueError, match="sections|field"):
        StudySpec.from_dict(malformed)


def test_source_requests_and_explicit_resolution_delegate_without_positional_objects(monkeypatch):
    class Owner:
        def __init__(self, data):
            self.data = copy.deepcopy(data)
        @classmethod
        def from_dict(cls, data):
            return cls(data)
        def to_dict(self):
            return copy.deepcopy(self.data)
        def add_subject(self, building=None, **options):
            self.data["subject"] = {"building": building, **options}
            return self
        def add_weather(self, weather=None, **options):
            self.data["weather"] = {"weather": weather, **options}
            return self
        def resolve_inputs(self, *, directory=None):
            self.data["resolved_at"] = directory
            return self
    monkeypatch.setitem(sys.modules, "epsm_workflows", types.SimpleNamespace(WorkflowSpec=Owner))
    study = Study(StudySpec("Requests", workflow=WORKFLOW))
    initial = study.spec
    study.add_subject(id="one", source={"kind": "synthetic"})
    study.add_weather(id="amy", request={"kind": "amy_batch"})
    assert study.resolve_inputs(directory="declared-output") is study
    assert initial.workflow == WORKFLOW
    assert study.spec.workflow["subject"]["building"] is None
    assert study.spec.workflow["weather"]["request"]["kind"] == "amy_batch"
    assert study.spec.workflow["resolved_at"] == "declared-output"


def test_unknown_authoring_type_is_rejected_but_opaque_saved_studies_still_open():
    with pytest.raises(ValueError, match="study type"):
        Study("Wrong", type="unknown", workflow=WORKFLOW)
    spec = StudySpec("Future", workflow=WORKFLOW, metadata={"type": "future-type"})
    assert Study.from_dict(spec.to_dict()).spec.metadata["type"] == "future-type"


def test_composed_schema_keeps_discriminators_and_standalone_input_schemas_usable():
    import jsonschema
    pytest.importorskip("epsm_workflows")
    from epsm_workflows import WorkflowSpec
    from epsm_core import Building
    study = Study("Schema metadata")
    schema = study.schema()
    workflow = schema["$defs"]["Workflow"]
    mappings = []
    def visit(value):
        if isinstance(value, dict):
            if "discriminator" in value:
                mappings.extend(value["discriminator"].get("mapping", {}).values())
            for key, item in value.items():
                if key != "x-epsm-inputs":
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(workflow)
    assert mappings
    for reference in mappings:
        assert reference.startswith("#/$defs/Workflow/")
        resolved = schema
        for part in reference[2:].split("/"):
            resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
        assert isinstance(resolved, dict)
    owner_inputs = WorkflowSpec.schema()["x-epsm-inputs"]
    assert workflow["x-epsm-inputs"] == owner_inputs
    glazing = Building(preset="illustrative-reference").facade.glazing.model_dump(mode="json")
    jsonschema.validate(glazing, workflow["x-epsm-inputs"]["facade.glazing"]["schema"])
