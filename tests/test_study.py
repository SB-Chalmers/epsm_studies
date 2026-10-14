import json

import pytest

from epsm_studies import PaperStudy


def test_protocol_roundtrip_and_overwrite_guard(tmp_path):
    config = {"depth": 2}
    study = PaperStudy(
        "renovation-paths",
        "How do energy and carbon trade off?",
        config,
        sources={"catalogue": "release-id"},
        plan_ids=("plan-id",),
    )
    config["depth"] = 3
    assert study.configuration["depth"] == 2
    path = study.save(tmp_path / "study.json")
    assert PaperStudy.from_dict(json.loads(path.read_text())).id == study.id
    study.save(path)
    with pytest.raises(ValueError, match="immutable"):
        PaperStudy("changed", "Another question").save(path)


def test_nested_inspection_and_serialization_cannot_change_protocol(tmp_path):
    study = PaperStudy(
        "renovation-paths",
        "How do energy and carbon trade off?",
        configuration={"depths": [1, 2]},
        sources={"catalogue": {"inputs": ["fixed-source"]}},
    )
    identity = study.id
    study.configuration["depths"].append(3)
    study.sources["catalogue"]["inputs"].append("new-source")
    study.to_dict()["configuration"]["depths"].append(4)
    assert study.configuration == {"depths": [1, 2]}
    assert study.sources == {"catalogue": {"inputs": ["fixed-source"]}}
    assert study.id == identity
    path = study.save(tmp_path / "study.json")
    assert PaperStudy.from_dict(json.loads(path.read_text())).id == identity


@pytest.mark.parametrize("name", ["short", "building" * 1000, "\n\t\x00ö🏠" * 1000])
def test_inspection_is_bounded_and_omits_configuration(name):
    study = PaperStudy(name, "Question", {"private-value": list(range(1000))})
    for representation in (repr(study), str(study)):
        assert len(representation) <= 120
        assert "PaperStudy(" in representation
        assert "private-value" not in representation
        assert "\n" not in representation
        assert "\t" not in representation


def test_plan_identities_cannot_contain_mutable_values():
    with pytest.raises(ValueError, match="plan identities"):
        PaperStudy("study", "Question", plan_ids=(["mutable"],))
