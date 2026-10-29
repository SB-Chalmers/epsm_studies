# Release 0.5.0 — the Workflows 0.5 cohort (29 October 2026)

Compatibility release. The `workflows` extra now requires Workflows 0.5.0
(`epsm_workflows[epsm]>=0.5.0,<0.6`), which carries Core 0.9.0, Data 0.7.0 and
EPSM 0.5.0. Study authoring, result archives and comparison APIs are unchanged.

# Release 0.4.0 — portable study authoring and outcomes

`StudySpec` keeps versioned metadata/protocol and reporting choices around the
Workflows-owned specification. `Study` delegates authoring, preflight, prepared
local execution and explicit Vera submission; reconstruction needs no execution
packages. Existing `PaperStudy` and comparison APIs remain supported.

`StudyResults` publishes immutable, relocatable archives of every planned case
and attempt with owner evaluation bundles, model/weather assets and checksums.
Metadata inspection is dependency-light; numerical signals load individually.
Coverage, explicit portfolio totals, baseline/engine differences, temporal energy
sums and CSV/JSON exports preserve unknown values and incomplete outcomes.
The `epsm-study` CLI calls the same collection, inspection and export operations.

See [the study platform guide](docs/study-platform.md) for APIs, optional extras,
portable formats and limitations. These features establish software contracts;
they do not establish empirical prediction accuracy.

# Studies 0.3.0 — engine comparison reports

The public interface includes `PaperStudy`, `compare_energy_results` and
`write_comparison_report`. These protocol and reporting functions use the Python
standard library and do not import Core or RC.

Comparison checks accepted engine results, shared snapshot/physical/weather
identities, complete expected hourly calendars, kWh units and annual/hourly
accounting before calculating annual, peak, monthly and hourly differences.
Reports retain failed cases explicitly and write portable HTML, JSON and paired
hourly CSV alongside the study protocol. Existing report artifacts are not
overwritten.

The [shared-fixture study](examples/engine_comparison/README.md) supplies an
explicit optional runner for actual Core and RC calculations. Its recorded
observations retain their original dependencies and assumptions. Software
agreement in these illustrative cases does not establish empirical accuracy.

# Release 0.2.0 — 15 October 2026

Protocol persistence and reuse identified by the existing immutable protocol identity.

Libraries emit through Python's standard logging without configuring output.
Instrumented operations accept optional keyword-only `log_context`; identifiers
stay separate from scientific inputs, saved models and cache keys. INFO shows
major stages; DEBUG adds decisions and timing. Standalone commands support
`--log-level`, including `OFF`, where the package provides a command.

The EPSM application configures the combined stderr and optional DEBUG JSONL
output with `configure_logging`; `enabled=False` disables both destinations.
Existing callers and supported older collaborator signatures remain supported.
No new mandatory dependency is introduced by the logging implementation.

The coordinated release was requested for manual review and local validation
because GitHub refused to start several hosted jobs due to account billing.
Hosted checks that did not run are not counted as passes. See the
[coordinated verification record](https://github.com/SB-Chalmers/epsm_development/blob/main/docs/logging-verification.md)
for exact tested revisions, executed checks and remaining limitations.
