# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EPSM Development contributors
# License: See LICENSE at the project root.
"""Public operation logging keeps calculation inputs and host configuration separate."""

import inspect
import logging

from epsm_studies import PaperStudy


def test_public_operation_accepts_explicit_context():
    parameter = inspect.signature(PaperStudy.save).parameters["log_context"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None


def test_import_does_not_install_output_handlers():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import epsm_studies; import logging; assert not any(isinstance(h, logging.StreamHandler) for h in logging.getLogger('epsm_studies').handlers)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stdout and not result.stderr


def test_save_keeps_protocol_identity_and_retains_prior_file(tmp_path, caplog):
    study = PaperStudy("logging", "Can we follow package handoffs?")
    identity = study.id
    with caplog.at_level(logging.DEBUG):
        path = study.save(
            tmp_path / "protocol.json", log_context={"study_id": identity}
        )
        before = path.read_bytes()
        study.save(path, log_context={"study_id": identity})
    assert path.read_bytes() == before and study.id == identity
    records = [r for r in caplog.records if hasattr(r, "epsm_event")]
    assert sum(r.epsm_event == "study.protocol.save.completed" for r in records) == 2
    assert any(r.epsm_event == "study.protocol.reused" for r in records)


def test_concurrent_saves_keep_independent_contexts(tmp_path, caplog):
    from concurrent.futures import ThreadPoolExecutor

    def save(name):
        study = PaperStudy(name, "Is concurrent context isolated?")
        return study.save(tmp_path / f"{name}.json", log_context={"case_id": name})

    with caplog.at_level(logging.DEBUG), ThreadPoolExecutor(max_workers=2) as pool:
        paths = list(pool.map(save, ("first", "second")))
    assert all(path.exists() for path in paths)
    selected = [
        r
        for r in caplog.records
        if getattr(r, "epsm_event", "") == "study.protocol.selected"
    ]
    assert len(selected) == 2
    for record in selected:
        assert record.epsm_context["case_id"] in record.epsm_details["path"]
