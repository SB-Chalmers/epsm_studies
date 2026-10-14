import json
import pytest

from epsm_studies import PaperStudy


def test_protocol_roundtrip_and_overwrite_guard(tmp_path):
    config = {"depth": 2}
    study = PaperStudy("renovation-paths", "How do energy and carbon trade off?", config,
                       sources={"catalogue": "release-id"}, plan_ids=("plan-id",))
    config["depth"] = 3
    assert study.configuration["depth"] == 2
    path = study.save(tmp_path / "study.json")
    assert PaperStudy.from_dict(json.loads(path.read_text())).id == study.id
    study.save(path)
    with pytest.raises(ValueError, match="immutable"):
        PaperStudy("changed", "Another question").save(path)
