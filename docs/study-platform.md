# Author, run and retain a study

`StudySpec` is the portable record. It owns a name, metadata, research protocol
and reporting choices, and embeds a serialized Workflows specification.
`Study` provides an editable draft around that record. Workflows owns sampling,
physical parameter bindings, portfolio expansion, baseline freezing and prepared
execution. EPSM, Core, RC and LCA retain their calculation and validation rules.
Studies does not create another physical model.

## Start from a reusable workflow

Install `epsm_studies[workflows,results]` with the compatible platform packages.
Supply explicitly prepared Building, Weather and engine settings as explained by
those owners. The calls below show the order; the caller supplies these objects.

```python
from dataclasses import asdict
from epsm_studies import Study

study = Study("Envelope alternatives", question="What changes heating?",
              method="lhs", samples=8, seed=17, engines=["epsm_rc"])
study.add_subject(building, id="building-1")
study.add_weather(weather, id="selected-year")
study.set("engine_settings", {"epsm_rc": {"settings": asdict(rc_settings)}})
study.vary("geometry.wwr", min=0.15, max=0.45, baseline=0.25)
report = study.preview()
assert report["ready"], report["diagnostics"]
study.save("outputs/experiment/study.json")
study.prepare("outputs/experiment/plan")
study.run("outputs/experiment/plan")
results = study.archive("outputs/experiment/plan", "outputs/experiment/archive-1")
```

Check the Workflows binding schema for the supported parameter names and
engine combinations. `Study.schema()` returns its configuration schema;
Workflows' capability discovery distinguishes available and unsupported options.
An editable draft can be incomplete. `validate()` and `preview()` expose missing
inputs before `prepare()` freezes the case matrix. No simulation starts during
these operations.

`study.spec` is immutable. Each authoring edit replaces it with a new revision;
earlier saved records and prepared plans are independent. An archive rejects a
workflow that differs from the frozen plan. Protocol and reporting additions can
refer to the same frozen workflow without rerunning it.

An output request is part of the workflow, before preparation. The default
workflow asks for hourly heating and annual delivered carrier energy. Request a
complete LCA explicitly when needed, and supply its assessment settings, material
factors and reference period. Reporting selections do not cause missing signals
to be calculated after execution.

## Execute locally or through Vera

For local workflows, `run(directory)` delegates to Workflows and uses the frozen
worker count. Explicit `workers=` and `retry_failed=` options go to its local
executor. Successful cases are reused. `cancel(directory)` requests graceful
local cancellation; active cases finish and their evidence remains retained.
`resume(directory)` clears that request without starting execution.

For a workflow prepared with `execution.executor="vera"`, pass a configured
public Workflows `VeraExecutor` to `run(directory, executor=client,
submit_options={...})`. Studies delegates staging and submission and returns the
submission receipt. It does not wait, poll or retrieve automatically. Use
`client.retrieve(directory)` before collecting results. Remote scheduler
cancellation is not exposed by this facade. Clients, credentials and connections
never enter `StudySpec`.

## Inspect results without the execution environment

```python
from epsm_studies import StudyResults

results = StudyResults.open("outputs/experiment/archive-1")
print(results.coverage())
rows = results.select(engine="epsm_rc")
heating = results.hourly(rows[0]["case_id"], "space_heating_demand_kwh")
months = results.aggregate_energy(rows[0]["case_id"], period="monthly")
results.export("outputs/experiment/summary.csv")
```

`open`, `table`, `select`, `coverage`, `summary`, `repr` and `str` use the loaded
index. They do not load arrays, import Workflows/engines, open a database or
calculate results. `hourly` and `time_axis` explicitly load one checksummed NumPy
file using `allow_pickle=False`. `evaluation_metadata` explicitly reads one
owner result's metadata, including LCA requirements/contributions and calculation
identities. `verify()` checks every archived file without decoding arrays.

The index has one row for every planned evaluation, with building, sample or
scenario, weather, engine, case, selected attempt and evaluation identities.
Real building identities remain distinct from physical model revisions and run
identities. `attempts(case)` retains every execution attempt, including failures
and interrupted attempts. A missing selected result remains visible as `not_run`
or a retained `running` attempt.

Executor success, engine acceptance, thermal coverage, delivery coverage and LCA
completeness are separate. Energy remains accessible when its assessment is
incomplete or failed. Missing impacts remain unknown; they never become zero.
Modern executor receipts retain EPSM's authoritative output checks. Legacy
inline results have structural availability information and keep their original
limitations.

General helpers deliberately require explicit choices:

- `aggregate_energy(case, period="monthly"|"annual")` sums a continuous hourly
  kWh signal; it cannot aggregate temperature or fill missing calendar hours.
- `portfolio_total(metric, case_ids=[...])` requires one case per identified
  building, one engine/sample/scenario, compatible units and assessment/energy
  boundaries. Missing values produce `value=None` and a labeled known subtotal.
- `difference(baseline, candidate, metric)` describes a change for one building
  and engine. A zero baseline has no percentage difference.
- `compare_engines(reference, candidate, expected_time_axis=...)` applies the
  existing strict shared-input comparator. Supply the intended calendar
  independently of observed output coverage.

These helpers do not fit models, select a preferred alternative or make claims
about prediction accuracy. CSV/JSON table exports include failures and unrun cases
unless the caller explicitly filters them.

## Portable formats and publication

The new formats are `epsm-study-spec/1` and `epsm-study-results/1`. Their versions
are independent of the package release. Existing `PaperStudy`, engine comparison
reports, inline evaluations and schema-3 prepared plans remain supported.
Studies preserves the embedded workflow's own version rather than copying its
scientific validator. Loading a draft or archive needs only Studies; editing or
executing it imports Workflows explicitly.

An archive contains `manifest.json` and a copied `execution/` tree with prepared
cases, model/weather assets, attempts, selected outcomes, owner evaluation
bundles and logs. Frozen `workflow.json` and cancellation metadata are retained
when present. Caches and locks are excluded. The index records checksums and
relative references. Evaluation bundles use the documented
`epsm-evaluation-bundle/1` owner format with separate `.npy` signals and calendar.
Original producer and calculation identities stay unchanged after relocation.

Collection validates the owner plan and attempts, checks referenced bundles, and
checks that outcomes stay unchanged during copying. The completion manifest is
published last. Opening a directory without that marker fails clearly. Existing
archives are immutable: identical recollection reuses one, while retries or other
changed evidence need a new target. Earlier attempts and archives remain intact.
Unknown formats, duplicate/nonfinite JSON, unsafe paths and symlinks are rejected.
Changed or missing arrays fail their explicit read; `verify()` checks all files.
A metadata-only open intentionally does not rehash large numerical outputs.

## Command harnesses

The installed `epsm-study` command and `python -m epsm_studies` call the same public
operations:

```sh
epsm-study archive outputs/experiment/study.json outputs/experiment/plan outputs/experiment/archive-1
epsm-study inspect outputs/experiment/archive-1 --verify
epsm-study export outputs/experiment/archive-1 outputs/experiment/summary.csv
```

Commands print a JSON receipt to stdout. `--log-level OFF|ERROR|WARNING|INFO|DEBUG`
controls stderr logging. Failed operations return status 2 without replacing
existing evidence; a successful inspection can describe an incomplete study.
