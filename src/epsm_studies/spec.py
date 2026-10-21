# SPDX-License-Identifier: MIT
"""Versioned study metadata wrapping an unchanged owner-authored workflow."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from ._records import canonical, digest, short


@dataclass(frozen=True, init=False, repr=False)
class StudySpec:
    """Immutable protocol and reporting choices with a portable workflow record.

    Parameters
    ----------
    name, question : str
        Human-readable name and optional research question.
    workflow : mapping
        Workflows-owned serialized specification, including its format version.
        This constructor checks finite JSON and preserves the record; it does not
        import Workflows or validate scientific/execution choices.
    metadata, protocol, reporting : mapping, optional
        Additional finite JSON study information. The explicit name and question
        supply their respective metadata/protocol fields.

    Notes
    -----
    Construction and inspection perform no I/O. Properties return detached copies.
    Use ``Study.validate()`` for owner validation before preparing execution.

    Examples
    --------
    >>> spec = StudySpec('Pilot', workflow={'format': 'epsm-workflow/1'})
    >>> StudySpec.from_dict(spec.to_dict()).id == spec.id
    True
    """
    _json: str

    def __init__(self, name: str, *, workflow: Mapping, question: str = "",
                 metadata: Mapping | None = None, protocol: Mapping | None = None,
                 reporting: Mapping | None = None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A study needs a nonempty name")
        if not isinstance(question, str):
            raise ValueError("The study question must be text")
        values = {"metadata": {} if metadata is None else metadata, "protocol": {} if protocol is None else protocol,
                  "workflow": workflow, "reporting": {} if reporting is None else reporting}
        if any(not isinstance(value, Mapping) for value in values.values()):
            raise ValueError("Study sections must be mappings")
        if not isinstance(workflow.get("format"), str) or not workflow["format"]:
            raise ValueError("The workflow needs its owner format version")
        data = {"format": "epsm-study-spec/1",
                "metadata": {**metadata} if metadata else {},
                "protocol": {**protocol} if protocol else {},
                "workflow": dict(workflow), "reporting": dict(reporting or {})}
        data["metadata"]["name"] = name
        data["protocol"]["question"] = question
        object.__setattr__(self, "_json", canonical(data))

    @property
    def id(self):
        return digest(json.loads(self._json))

    @property
    def name(self):
        return self.metadata["name"]

    @property
    def question(self):
        return self.protocol["question"]

    @property
    def metadata(self):
        return json.loads(self._json)["metadata"]

    @property
    def protocol(self):
        return json.loads(self._json)["protocol"]

    @property
    def workflow(self):
        return json.loads(self._json)["workflow"]

    @property
    def reporting(self):
        return json.loads(self._json)["reporting"]

    def to_dict(self):
        """Return the versioned record and its content identity, without I/O."""
        return {"id": self.id, **json.loads(self._json)}

    @classmethod
    def from_dict(cls, value: Mapping):
        """Validate a Studies envelope without interpreting the embedded workflow."""
        data = dict(value)
        identity = data.pop("id", None)
        if data.pop("format", None) != "epsm-study-spec/1":
            raise ValueError("Unsupported study specification format")
        if set(data) != {"metadata", "protocol", "workflow", "reporting"}:
            raise ValueError("Study specification has missing or unexpected sections")
        if not isinstance(data["metadata"], Mapping) or not isinstance(data["protocol"], Mapping):
            raise ValueError("Study metadata and protocol must be mappings")
        metadata, protocol = dict(data.pop("metadata")), dict(data.pop("protocol"))
        name = metadata.pop("name", None)
        question = protocol.pop("question", "")
        spec = cls(name, question=question, metadata=metadata, protocol=protocol, **data)
        if identity is not None and spec.id != identity:
            raise ValueError("Study specification identity differs from its content")
        return spec

    def summary(self):
        """Return loaded identity, name and section counts without owner imports."""
        return {"id": self.id, "name": self.name, "question": self.question,
                "workflow_format": self.workflow["format"],
                "reporting_fields": tuple(self.reporting)}

    def with_workflow(self, workflow: Mapping):
        """Create a new draft revision while retaining protocol/reporting choices."""
        return type(self)(self.name, question=self.question, workflow=workflow,
                          metadata=self.metadata, protocol=self.protocol, reporting=self.reporting)

    def __repr__(self):
        return f"StudySpec(name={short(self.name)}, id='{self.id[:12]}', workflow={short(self.workflow['format'], 35)})"

    __str__ = __repr__
