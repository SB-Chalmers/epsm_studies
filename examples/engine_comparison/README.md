# Core and RC fixture comparison

This named study runs both engines annually from the same captured physical
Building snapshot, weather and load reference area. Studies owns the protocol,
comparison and report; the public Core/RC APIs own the science. This small runner
does not add scheduling, caches or distributed execution: those remain in
`epsm_workflows`.

The four fixtures adapt RC's annual shared-input and geometry regression tests:

| Fixture | Floor area | Load reference area | Weather | People sensible fraction |
|---|---:|---:|---|---:|
| Controlled 0% | 48 m² | 40 m² | Explicit synthetic constant 2023 | 0 |
| Controlled 100% | 48 m² | 40 m² | Explicit synthetic constant 2023 | 1 |
| Rectangle | 200 m² | 180 m² | Caller-supplied 2023 EPW | 0.6 |
| Concave | 300 m² | 270 m² | Caller-supplied 2023 EPW | 0.6 |

These are **illustrative software fixtures, not measured buildings**. The named
`illustrative-reference` preset explicitly selects fabric, glazing, HVAC and
base operation. `fixtures.json` declares geometry, hourly equipment heat shares,
people/equipment/lighting partitions, reference areas and a shared prescribed
18 °C monthly ground boundary. That boundary is a controlled comparison choice,
not a recommended ground model for Sweden. RC explicitly omits latent/supply
controls and self-shadowing; EnergyPlus keeps geometric shadowing. The concave
case therefore includes a known solar-method difference.

Install matching reviewed Core/Data/RC releases and Studies in one environment,
including Core's `geometry` extra. No engine dependencies are installed by the
base Studies package. EnergyPlus 24.2 and its adjacent schema are required. From
this repository:

```sh
python examples/engine_comparison/run.py \
  --weather /absolute/path/to/goteborg.epw \
  --energyplus /absolute/path/to/energyplus \
  --output /absolute/path/to/new-study-output
```

The weather argument is mandatory; no city file is chosen implicitly. The two
controlled cases generate a clearly labelled synthetic EPW. The output directory
must be new. Execution writes:

- `report.html`: standalone annual, peak, hourly-error and monthly comparison,
  with per-case assumptions and input identities;
- `comparison.json`: machine-readable statistics, failed cases and engine treatment;
- `hourly.csv`: all paired hourly heating values and candidate-minus-reference values;
- `protocol.json`: immutable `PaperStudy`, declared fixtures and package source hashes;
- `supplied.epw` and `controlled.epw`: the captured weather bytes;
- each case's `building.json` and the engines' native artifacts.

Input mismatches, rejected engine results, missing/shifted hours, incorrect units,
nonfinite values and broken annual/hourly accounting prevent a comparison.
Individual failed cases remain in the report and the command exits nonzero.
Relative differences with zero reference demand are undefined, not zero.
Core and RC source hashes/version identities, weather checksums and the EnergyPlus
executable/schema hashes are retained. Source checkouts additionally record Git
revisions and whether tracked files were modified.

Interpret annual differences alongside peaks, hourly RMSE, monthly patterns and
declared engine omissions. Close annual totals do not establish empirical accuracy
or justify tuning physical assumptions to force agreement. Extending the fixture
set is a new protocol identity, rather than an edit to a previous run.

## Reference observations

Executed with Core `76b9c93978d26d5f27f0616b51fbb1ca19fb6801` (0.4.0),
RC `d8f42ab69e61cfe580f234b20ddc47cf6d056e59` (0.4.0), Data
`bc8449402b9e0dbe0ea85ff76c954cf36d209f86` (0.6.0), and EnergyPlus
`24.2.0-94a887817b` on Python 3.12.3. The supplied Göteborg EPW SHA256 was
`30f267c63fb318a7dd808a8d018b9d593f380f8599a21615672c9094e1aad36b`.
All four cases produced accepted, finite 8,760-hour results with balanced
annual/hourly heating accounting. These are observations, not pass thresholds:

| Fixture | EnergyPlus heating kWh | RC heating kWh | RC − EnergyPlus |
|---|---:|---:|---:|
| Controlled 0% | 6,184.745 | 6,009.141 | −2.84% |
| Controlled 100% | 5,920.662 | 5,738.723 | −3.07% |
| Göteborg rectangle | 9,852.899 | 9,371.597 | −4.88% |
| Göteborg concave | 14,703.166 | 13,910.422 | −5.39% |

In the two Göteborg cases RC's peak hourly-average heating power was 12.35% and
11.87% higher despite lower annual demand. Differences concentrate in spring
and autumn; January/February totals are much closer. No coefficients were tuned
to obtain these numbers. Changing the fixture, weather or model choices requires
another run and protocol; agreement in these cases does not establish a general
error bound.
