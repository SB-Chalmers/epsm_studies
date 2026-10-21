# SPDX-License-Identifier: MIT
"""User-facing study draft; workflow methods delegate to their owning package."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ._logging import operation
from ._records import publish_json, read_json, short, digest
from .spec import StudySpec


def _workflow_type():
    try:
        from epsm_workflows import WorkflowSpec
    except ImportError as error:
        raise ImportError("Install epsm_studies[workflows] to author or execute workflows") from error
    return WorkflowSpec


class Study:
    """Editable study draft with immutable revision records and lazy execution imports.

    ``Study(spec)`` and ``Study.open(path)`` need only Studies. Starting a new
    template, editing workflow choices, validation and execution require the
    optional Workflows integration. Edits return this draft and replace ``spec``
    with a new immutable revision; previously prepared inputs remain unchanged.

    Parameters
    ----------
    name : str or StudySpec
        A new study name or an existing immutable specification.
    type : str
        Study metadata label; default ``parametric``.
    method, samples, seed
        Passed to Workflows' template when no workflow record is supplied.
    workflow : mapping or WorkflowSpec, optional
        Existing owner workflow data. Supplying it avoids importing Workflows.
    engines : sequence of str, optional
        Explicit engine selections, delegated to Workflows.
    """
    def __init__(self, name: str | StudySpec, *, question: str = "", workflow=None,
                 type: str = "parametric", method: str = "lhs", samples: int = 100,
                 seed: int = 0, engines=None, metadata=None, protocol=None, reporting=None):
        if isinstance(name, StudySpec):
            if workflow is not None:
                raise ValueError("Supply a StudySpec or a workflow, not both")
            self._spec = name
        else:
            selected_type = (metadata or {}).get("type", type)
            if selected_type != "parametric":
                raise ValueError("Unsupported study type; use parametric and choose its workflow method")
            if workflow is None:
                workflow = _workflow_type().template(method=method, samples=samples, seed=seed)
            if hasattr(workflow, "to_dict"):
                workflow = workflow.to_dict()
            self._spec = StudySpec(name, question=question, workflow=workflow,
                                   metadata={"type": type, **(metadata or {})},
                                   protocol=protocol, reporting=reporting)
        if engines is not None:
            self.set("engines", list(engines))

    @property
    def spec(self) -> StudySpec:
        return self._spec

    @property
    def name(self):
        return self.spec.name

    @property
    def question(self):
        return self.spec.question

    @property
    def id(self):
        return self.spec.id

    def to_dict(self):
        return self.spec.to_dict()

    @classmethod
    def from_dict(cls, value: Mapping):
        """Restore a study draft without importing any execution package."""
        return cls(StudySpec.from_dict(value))

    @classmethod
    def open(cls, path):
        """Read a specification JSON file or completed result archive metadata."""
        path = Path(path)
        if path.is_dir():
            from .results import StudyResults
            return cls(StudyResults.open(path).spec)
        return cls.from_dict(read_json(path))

    @operation("study.spec.save")
    def save(self, path):
        """Publish JSON exclusively; repeated identical saves reuse the file."""
        path = Path(path)
        try:
            return publish_json(path, self.to_dict())
        except FileExistsError:
            if type(self).open(path).id == self.id:
                return path
            raise FileExistsError("Study specification exists; choose a new path") from None

    def _owner(self):
        return _workflow_type().from_dict(self.spec.workflow)

    def _edit(self, method, *args, **kwargs):
        owner = self._owner()
        result = getattr(owner, method)(*args, **kwargs)
        if result is not None and hasattr(result, "to_dict"):
            owner = result
        self._spec = self.spec.with_workflow(owner.to_dict())
        return self

    def set(self, binding, value, **options):
        """Delegate a fixed input/configuration choice to Workflows; update this draft."""
        return self._edit("set", binding, value, **options)

    def vary(self, binding, **options):
        """Delegate a parameter domain, distribution and baseline to Workflows."""
        return self._edit("vary", binding, **options)

    def add_subject(self, building=None, **options):
        """Delegate an independent physical subject and optional group assignment."""
        return self._edit("add_subject", building, **options)

    def add_weather(self, weather=None, **options):
        """Delegate weather artifacts and explicit subject assignments."""
        return self._edit("add_weather", weather, **options)

    def add_scenario(self, name, building, **options):
        """Delegate a named physical alternative without changing its baseline."""
        return self._edit("add_scenario", name, building, **options)

    def schema(self):
        """Compose the Studies envelope with Workflows' generated typed schema."""
        return StudySpec.schema(_workflow_type().schema())

    def resolve_inputs(self, *, directory=None):
        """Explicitly acquire declared inputs through their owners; revise this draft.

        File/provider access occurs only in the delegated resolution operation.
        Supply an output directory for weather acquisition. A failed resolution
        leaves this facade's earlier immutable specification unchanged.
        """
        return self._edit("resolve_inputs", directory=directory)

    def validate(self):
        """Ask Workflows and model owners for authoring/preflight diagnostics."""
        return self._owner().validate()

    def preview(self):
        """Ask Workflows to expand the intended case matrix without execution."""
        return self._owner().preview()

    def prepare(self, directory):
        """Freeze independent execution inputs using Workflows' public operation."""
        return self._owner().prepare(directory)

    def run(self, directory, *, executor=None, submit_options=None, **options):
        """Delegate execution using the frozen local/Vera selection.

        Local execution uses the frozen worker count unless explicitly overridden
        and returns Workflows' outcome counts. Vera requires a configured public
        ``VeraExecutor`` instance; this method stages then submits and returns its
        receipt. It does not wait or retrieve. Transport credentials and clients
        are never serialized. Retrieve explicitly before collecting an archive.
        """
        _workflow_type()
        from epsm_workflows import run_local, validate_plan, VeraExecutor
        root = Path(directory)
        plan = validate_plan(root)
        frozen = read_json(root / "workflow.json") if (root / "workflow.json").exists() else {}
        expected = plan.get("environment", {}).get("workflow_id")
        if expected is not None and digest(frozen) != expected:
            raise ValueError("Retained workflow differs from its frozen plan identity")
        execution = frozen.get("execution", {})
        if execution.get("executor", "local") == "vera":
            if not isinstance(executor, VeraExecutor):
                raise ValueError("Vera execution requires an explicit configured Workflows VeraExecutor")
            if options:
                raise ValueError("Supply Vera scheduler options through submit_options")
            executor.stage(root)
            return executor.submit(root, **(submit_options or {}))
        if executor is not None or submit_options:
            raise ValueError("The prepared workflow selected local execution")
        options.setdefault("workers", execution.get("workers", 1))
        return run_local(root, **options)

    def cancel(self, directory):
        """Request graceful local cancellation; existing attempts remain retained."""
        from epsm_workflows import cancel
        root = Path(directory)
        if (root / "workflow.json").exists() and read_json(root / "workflow.json").get("execution", {}).get("executor") == "vera":
            raise ValueError("Remote cancellation is not exposed by the Studies facade; use the scheduler explicitly")
        return cancel(root)

    def resume(self, directory):
        """Clear a local cancellation request without executing or discarding evidence."""
        from epsm_workflows import resume
        root = Path(directory)
        if (root / "workflow.json").exists() and read_json(root / "workflow.json").get("execution", {}).get("executor") == "vera":
            raise ValueError("Remote resume is not exposed by the Studies facade; use the scheduler explicitly")
        return resume(root)

    def archive(self, execution_directory, directory):
        """Collect verified outcomes into a new portable, immutable result snapshot."""
        from .results import StudyResults
        return StudyResults.collect(self.spec, execution_directory, directory)

    def results(self, directory):
        """Open an existing result archive without Workflows or model imports."""
        from .results import StudyResults
        return StudyResults.open(directory)

    def summary(self):
        return self.spec.summary()

    def __repr__(self):
        return f"Study(name={short(self.spec.name)}, revision='{self.id[:12]}')"

    __str__ = __repr__
