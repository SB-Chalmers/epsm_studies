# EPSM Studies

<!-- EPSM introduction: Pocket CAD -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/epsm_studies-dark.png">
  <img src="docs/assets/brand/epsm_studies.png" width="64" height="64" alt="EPSM Studies — research records">
</picture>

Record research protocols, compare energy results and keep study evidence and historical archives together.

[Explore the EPSM platform](https://github.com/SB-Chalmers/epsm/blob/main/docs/platform.md)
<!-- /EPSM introduction -->

Portable EPSM study definitions, research protocols and retained result archives.
Version **0.4.0** adds delegated study authoring, complete result collections,
general summaries and validated engine-result comparisons;
see the [release notes](RELEASE_NOTES.md) for its public interface and scope.
`PaperStudy` records a study setup; reusable designs, optimisation and execution
belong to `epsm_workflows`. Existing named study implementations are archived
pending later decisions by the maintainer.

```python
from epsm_studies import PaperStudy

study = PaperStudy(
    name="renovation-alternatives",
    question="Which physical renovation sequences improve energy and carbon?",
    configuration={"max_depth": 2, "assessment_period_years": 50},
    sources={"catalogue": "reviewed-release-id"},
    plan_ids=("prepared-workflow-plan-id",),
)
study.save("outputs/renovation-alternatives/protocol.json")
```

These illustrative values are explicit protocol choices, not scientific defaults.
Changing the question or assumptions creates another protocol identity.
`configuration` and `sources` return independent copies for inspection; editing
those copies does not change the protocol or its identity. Construct another
`PaperStudy` to record changed assumptions.

## Engine comparison reports

`compare_energy_results` checks shared input identities, accepted results,
complete expected hourly coverage, units and annual/hourly accounting before
calculating annual, peak, monthly and hourly differences. `write_comparison_report`
stores a study's portable HTML report, JSON and paired hourly CSV, retaining failed
cases explicitly. Both APIs work without importing engine packages.

The [Core/RC fixture study](examples/engine_comparison/README.md) runs real annual
EnergyPlus 24.2 and RC cases from captured shared Building inputs. It demonstrates
study-owned reporting while leaving simulation to Core/RC and reusable execution
to Workflows. The fixture assumptions are explicit and do not establish empirical
validation of either engine.

## Historical Workflows transfer

`archive/workflows_2026_10_14/` preserves tracked source, tests, configurations,
examples and documentation from Workflows commit
`1e49fa212f26ed80e6c2dce173cf5caa87a8b5b2`. `ARCHIVE.json` lists SHA256 checksums.
Simulation outputs and external raw datasets are not copied.

The formerly importable `src/epsm_studies/legacy_workflows/` implementations
now reside in `archive/2026-10-14/src/epsm_studies/legacy_workflows/`. Their
original bytes and package metadata are recorded in
[ARCHIVE.json](archive/2026-10-14/ARCHIVE.json).
The legacy extra and compatibility imports have been retired. These files are
unsupported historical material, excluded from the installed package and normal
test discovery. They have no execution, repair or reproduction commitment.
The generic `PaperStudy` API and its tests remain active.

The transfer includes national stock exploration, MF revisions, cohort transfer,
archetype diagnosis, the surrogate campaign and weather-imputation study sources.
Old assumptions and source hashes remain inspectable. See the
[archive index](archive/README.md) for the retained collections and their scope.

## Data validation transfer

`imports/epsm_data_harmonisation/` retains historical LoD2 fitting/validation,
frozen-baseline and cohort-profile evidence transferred from Data. `TRANSFER.json`
records original relative paths and verified checksums. This collection is archived
evidence: its location is retained because Data source provenance refers to these
paths. It is excluded from installation and normal test discovery. Current
construction defaults and original source evidence remain owned by Data.

## Operation logging

Library calls use Python's standard `logging` module and install no console or
file output. Instrumented operations accept optional keyword-only `log_context`
with small identifier mappings; nested events carry operation and parent IDs.
INFO describes major stages; DEBUG exposes selections, conversions and caches.
Logging context does not change physical models or scientific cache inputs.

For an application using EPSM's coordinated logging setup:

```python
from epsm import configure_logging, reset_logging

configure_logging(directory="outputs/example")  # INFO stderr, DEBUG JSONL
# Run operations here.
configure_logging(enabled=False)  # Stop console and file logging.
reset_logging()  # Restore the host application's settings.
```

EPSM is needed only for this combined configuration, not for ordinary library
logging. Existing scripts can keep using `logging.basicConfig(level=logging.INFO)`.

## Portable study drafts

`StudySpec` keeps study metadata, protocol and reporting choices around a
Workflows-owned serialized specification. `Study` provides convenient authoring
methods that delegate to Workflows. Existing `PaperStudy` records remain supported.

```python
from epsm_studies import Study, StudySpec

# Existing workflow data can be inspected without installing engines or Workflows.
spec = StudySpec("Pilot", question="What changes heating?",
                 workflow={"format": "epsm-workflow/1"})
study = Study(spec)
assert Study.from_dict(study.to_dict()).id == study.id
```

The minimal workflow above illustrates the portable envelope; it is not an
executable experiment. Install `epsm_studies[workflows]` to start a real template,
configure `.set(...)`, `.vary(...)`, `.add_subject(...)`, `.add_weather(...)` and
`.add_scenario(...)`, explicitly `.resolve_inputs(...)` when acquisition was requested, then `.validate()`, `.preview()` and `.prepare(directory)`.
Workflows owns those scientific and execution rules. Each edit creates an
independent `study.spec` revision; earlier prepared plans are fixed.
`study.save(path)` refuses to replace a different specification. `Study.open(path)`
restores the draft without importing execution packages.

After execution, `study.archive(plan_directory, archive_directory)` publishes a
portable `StudyResults` snapshot. Every planned case remains visible, including
failures, missing results and incomplete assessments. Reopen it with
`StudyResults.open(archive_directory)` without Workflows or engine packages.
`coverage()`, `table()` and `select(...)` read only its loaded index. Explicit
`hourly(case, signal)` and `time_axis(case)` operations load individual checked
NumPy arrays; install `epsm_studies[results]` for these calls. A changed retry
outcome needs a new archive directory; an identical recollection is reused.

See [the study platform guide](docs/study-platform.md) for complete public APIs,
result boundaries, supported formats and the `epsm-study` command harnesses.

`Study.schema()` composes one complete study document schema from the Studies
envelope and Workflows-owned scientific schema. `StudySpec.schema()` remains
dependency-light. General `describe(metric, case_ids=[...])` summaries retain
missing counts and require comparable units and boundaries.
