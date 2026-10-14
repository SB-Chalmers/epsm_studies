"""Small, serializable record of a paper's research question and chosen inputs."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class PaperStudy:
    """A named scientific protocol referencing prepared workflow plans.

    Configuration contains paper-specific assumptions. Source revisions and
    immutable plan identities make those choices reviewable independently of
    executor locations. Construct a new protocol when assumptions change.
    """
    name: str
    question: str
    configuration: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    plan_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.name.strip() or not self.question.strip():
            raise ValueError("A study needs a name and research question")
        # Copy caller-owned dictionaries and validate finite JSON data.
        for name in ("configuration", "sources"):
            object.__setattr__(self, name, json.loads(json.dumps(getattr(self, name), allow_nan=False)))
        object.__setattr__(self, "plan_ids", tuple(self.plan_ids))

    @property
    def id(self):
        data = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {"id": self.id, **asdict(self)}

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
