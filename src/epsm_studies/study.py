"""Small, serializable record of a paper's research question and chosen inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, init=False, repr=False)
class PaperStudy:
    """A named scientific protocol referencing prepared workflow plans.

    Configuration contains paper-specific assumptions. Source revisions and
    immutable plan identities make those choices reviewable independently of
    executor locations. Construct a new protocol when assumptions change.
    """

    name: str
    question: str
    plan_ids: tuple[str, ...]
    _configuration_json: str
    _sources_json: str

    def __init__(self, name, question, configuration=None, sources=None, plan_ids=()):
        if not isinstance(name, str) or not isinstance(question, str):
            raise ValueError("Study name and research question must be text")
        if not name.strip() or not question.strip():
            raise ValueError("A study needs a name and research question")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "question", question)
        # JSON strings keep nested values fixed. Inspection returns independent
        # dictionaries, so even a nested edit cannot change this protocol.
        for field, value in (("configuration", configuration), ("sources", sources)):
            if value is None:
                value = {}
            if not isinstance(value, dict):
                raise ValueError(f"Study {field} must be a dictionary")
            payload = json.dumps(
                value, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            object.__setattr__(self, f"_{field}_json", payload)
        plan_ids = tuple(plan_ids)
        if any(not isinstance(value, str) or not value.strip() for value in plan_ids):
            raise ValueError("Study plan identities must be nonempty strings")
        object.__setattr__(self, "plan_ids", plan_ids)

    @property
    def configuration(self):
        """Return an independent copy of the paper-specific assumptions."""
        return json.loads(self._configuration_json)

    @property
    def sources(self):
        """Return an independent copy of the recorded input references."""
        return json.loads(self._sources_json)

    def _payload(self):
        return {
            "name": self.name,
            "question": self.question,
            "configuration": self.configuration,
            "sources": self.sources,
            "plan_ids": self.plan_ids,
        }

    def __repr__(self):
        name = self.name if len(self.name) <= 64 else self.name[:61] + "..."
        while len(repr(name)) > 70:
            name = name[:-4] + "..."
        return f"PaperStudy(name={name!r}, plans={len(self.plan_ids)})"

    __str__ = __repr__

    @property
    def id(self):
        data = json.dumps(
            self._payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {"id": self.id, **self._payload()}

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        identity = value.pop("id", None)
        study = cls(**value)
        if identity is not None and identity != study.id:
            raise ValueError("Study identity does not match its configuration")
        return study

    def save(self, path):
        """Write a protocol once; a different protocol cannot overwrite it."""
        path = Path(path)
        content = json.dumps(self.to_dict(), indent=2, allow_nan=False) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if self.from_dict(json.loads(path.read_text())).id != self.id:
                raise ValueError("Existing study protocol is immutable")
            return path
        with path.open("x") as stream:
            stream.write(content)
        return path
