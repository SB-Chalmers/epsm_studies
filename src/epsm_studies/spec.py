# SPDX-License-Identifier: MIT
"""Versioned study metadata wrapping an unchanged owner-authored workflow."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
from copy import deepcopy

from ._records import canonical, digest, short


# This one declaration defines the Studies envelope's stored validation and
# exported schema. Workflow science remains an opaque object unless its owner
# explicitly supplies its generated schema for composition.
_FIELDS = {
    "format": {"const": "epsm-study-spec/1"},
    "id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "metadata": {"type": "object", "required": ["name"],
                 "properties": {"name": {"type": "string", "minLength": 1, "pattern": r"\S"}}},
    "protocol": {"type": "object", "properties": {"question": {"type": "string"}}},
    "workflow": {"type": "object", "required": ["format"],
                 "properties": {"format": {"type": "string", "minLength": 1, "pattern": r"\S"}}},
    "reporting": {"type": "object"},
}
_REQUIRED = tuple(field for field in _FIELDS if field != "id")


def _validate_field(value, definition, field):
    """Validate only the small fixed vocabulary used by our envelope table."""
    if "const" in definition and value != definition["const"]:
        raise ValueError(f"Unsupported study specification field: {field}")
    kind = definition.get("type")
    if kind == "object":
        if not isinstance(value, Mapping):
            raise ValueError(f"Study section must be a mapping: {field}")
        if any(name not in value for name in definition.get("required", [])):
            raise ValueError(f"Study section is missing a required field: {field}")
        for name, rule in definition.get("properties", {}).items():
            if name in value:
                _validate_field(value[name], rule, f"{field}.{name}")
    elif kind == "string":
        if not isinstance(value, str) or len(value) < definition.get("minLength", 0):
            raise ValueError(f"Study field must be valid text: {field}")
        if "pattern" in definition and re.search(definition["pattern"], value) is None:
            raise ValueError(f"Study field has an invalid text value: {field}")


def _validate_envelope(value):
    if not isinstance(value, Mapping) or set(value) - set(_FIELDS) or set(_REQUIRED) - set(value):
        raise ValueError("Study specification has missing or unexpected sections")
    for field, item in value.items():
        _validate_field(item, _FIELDS[field], field)
    canonical(value)


def _rebase_workflow_schema(value):
    """Keep owner local references valid below the enclosing document root."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "x-epsm-inputs":
                # Capability metadata contains independently usable owner schemas,
                # each with its own local $defs. It is not a subtree evaluated
                # against the enclosing workflow's schema root.
                result[key] = deepcopy(item)
            elif key == "discriminator" and isinstance(item, dict):
                discriminator = deepcopy(item)
                if isinstance(discriminator.get("mapping"), dict):
                    discriminator["mapping"] = {
                        name: "#/$defs/Workflow" + reference[1:]
                        if isinstance(reference, str) and reference.startswith("#") else reference
                        for name, reference in discriminator["mapping"].items()}
                result[key] = discriminator
            elif key in {"$ref", "$dynamicRef"} and isinstance(item, str) and item.startswith("#"):
                result[key] = "#/$defs/Workflow" + item[1:]
            else:
                result[key] = _rebase_workflow_schema(item)
        return result
    if isinstance(value, list):
        return [_rebase_workflow_schema(item) for item in value]
    return value


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
        values = {"metadata": {} if metadata is None else metadata, "protocol": {} if protocol is None else protocol,
                  "workflow": workflow, "reporting": {} if reporting is None else reporting}
        if any(not isinstance(value, Mapping) for value in values.values()):
            raise ValueError("Study sections must be mappings")
        data = {"format": "epsm-study-spec/1",
                "metadata": {**metadata} if metadata else {},
                "protocol": {**protocol} if protocol else {},
                "workflow": dict(workflow), "reporting": dict(reporting or {})}
        data["metadata"]["name"] = name
        data["protocol"]["question"] = question
        _validate_envelope(data)
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
        _validate_envelope(value)
        data = dict(value)
        identity = data.pop("id", None)
        data.pop("format")
        metadata, protocol = dict(data.pop("metadata")), dict(data.pop("protocol"))
        name = metadata.pop("name", None)
        question = protocol.pop("question", "")
        spec = cls(name, question=question, metadata=metadata, protocol=protocol, **data)
        if identity is not None and spec.id != identity:
            raise ValueError("Study specification identity differs from its content")
        return spec

    @classmethod
    def schema(cls, workflow_schema=None):
        """Export the single Studies JSON Schema, optionally composing its owner.

        Without ``workflow_schema``, this standard-library-only operation treats
        the workflow as opaque versioned data. Passing Workflows' generated
        schema embeds it under ``$defs.Workflow`` and rebases its local refs;
        scientific rules and definitions are never copied into Studies code.
        The returned schema is an independent dictionary and does no I/O.
        """
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "title": "StudySpec", "type": "object",
                  "additionalProperties": False, "required": list(_REQUIRED),
                  "properties": deepcopy(_FIELDS)}
        if workflow_schema is not None:
            if not isinstance(workflow_schema, Mapping):
                raise TypeError("Supply the owning workflow's schema mapping")
            schema["$defs"] = {"Workflow": _rebase_workflow_schema(deepcopy(dict(workflow_schema)))}
            schema["properties"]["workflow"] = {"$ref": "#/$defs/Workflow"}
        return schema

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
