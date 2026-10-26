# Catalogue validation: national GIS-lake sample

26 October 2026. This run applies the same contract and scoring as the
[Uddevalla run](README.md): epsm_data
[`docs/validation.md`](https://github.com/SB-Chalmers/epsm_data/blob/codex/lod2-catalogue/docs/validation.md),
catalogue `92d776d`. The buildings come from the national epsm_db GIS lake.
Runner: [`national_three_state.py`](national_three_state.py). Results:
[`results_national/tables.md`](results_national/tables.md),
[`buildings.csv`](results_national/buildings.csv),
[`excluded.csv`](results_national/excluded.csv) and
[`summary.json`](results_national/summary.json), which includes the manifest.

## Result

| 543 buildings, 28 cohorts | Result | Provisional target |
| --- | ---: | ---: |
| Coverage: measured between Advanced and Existing (480 buildings with a range) | **44 %** | ≥ 70 % |
| Match: some state within ±20 % | **55 %** | ≥ 50 % |
| Existing-state median r | 1.07 | reported |
| Advanced-state median r | 0.54 | reported |
| Selected state E / S / A / SE.07 / none | 137 / 91 / 53 / 16 / 246 | reported |
| Measured below / inside / above the simulated range | 90 / 209 / 244 | — |

27 of 28 cohorts have at least 10 buildings, so for the first time the contract can be
evaluated per cohort.

- **4 cohorts meet both targets:** single-family SE.02, multifamily SE.01, and schools SE.01
  and SE.02.
- **17 cohorts reach the 50 % match target.**
- **4 reach the 70 % coverage target** (the same four).

The national figures repeat the Uddevalla pattern (coverage 44 %, match 57 %) on a
sample about seven times larger.

The failures are not random. **The simulated era gradient is steeper than the measured
one.**

- **Older single-family houses are overpredicted.** Measured heating is below even the
  Advanced state in 10 of 20 SE.01 houses and 11 of 20 SE.03 houses.
- **Newer multifamily blocks, offices and schools are underpredicted.** Measured heating is
  above the Existing state in 14–19 of 20 buildings in multifamily SE.06–SE.07 and offices
  SE.03–SE.06.
- **Median delivered heating per m² Atemp, measured against model Existing:**

| Type | SE.01 | SE.02 | SE.03 | SE.04 | SE.05 | SE.06 | SE.07 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Single-family | 46 / 85 | 71 / 118 | 58 / 91 | 46 / 47 | 52 / 40 | 32 / 35 | 19 / 28 |
| Multifamily | 97 / 123 | 94 / 94 | 86 / 94 | 60 / 54 | 70 / 70 | 54 / 47 | 34 / 11 |
| Office | 97 / 127 | 82 / 70 | 63 / 67 | 67 / 50 | 66 / 37 | 37 / 24 | 25 / 6 |
| School | 121 / 144 | 106 / 141 | 98 / 114 | 67 / 98 | 75 / 71 | 59 / 58 | 45 / 35 |

Measured heating falls about 2.4–4× from SE.01 to SE.07. The model falls 3–20×.

## Cohort table

Selected = closest state within ±20 %. A single SE.07 state has no range, so coverage is
"—" for SE.07. `*` n < 10.

| Cohort | n | Coverage | Match | Existing median r | Advanced median r | Selected E / S / A / SE.07 / none | Measured below / inside / above range |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_family SE.01 | 20 | 50% | 55% | 1.95 | 1.03 | 1 / 6 / 4 / 0 / 9 | 10 / 10 / 0 |
| single_family SE.02 | 20 | 75% | 95% | 1.55 | 0.88 | 4 / 8 / 7 / 0 / 1 | 4 / 15 / 1 |
| single_family SE.03 | 20 | 35% | 55% | 1.80 | 1.06 | 2 / 5 / 4 / 0 / 9 | 11 / 7 / 2 |
| single_family SE.04 | 20 | 30% | 65% | 1.11 | 0.67 | 6 / 5 / 2 / 0 / 7 | 5 / 6 / 9 |
| single_family SE.05 | 20 | 35% | 50% | 0.83 | 0.47 | 3 / 6 / 1 / 0 / 10 | 2 / 7 / 11 |
| single_family SE.06 | 20 | 40% | 60% | 1.20 | 0.79 | 2 / 6 / 4 / 0 / 8 | 7 / 8 / 5 |
| single_family SE.07 | 20 | — | 30% | 1.30 | — | 0 / 0 / 0 / 6 / 14 | 19 / 0 / 1 |
| multi_family SE.01 | 20 | 80% | 90% | 1.19 | 0.49 | 10 / 8 / 0 / 0 / 2 | 0 / 16 / 4 |
| multi_family SE.02 | 20 | 45% | 80% | 0.99 | 0.50 | 15 / 1 / 0 / 0 / 4 | 0 / 9 / 11 |
| multi_family SE.03 | 20 | 45% | 70% | 1.07 | 0.50 | 5 / 6 / 3 / 0 / 6 | 1 / 9 / 10 |
| multi_family SE.04 | 20 | 45% | 55% | 1.07 | 0.47 | 8 / 1 / 2 / 0 / 9 | 2 / 9 / 9 |
| multi_family SE.05 | 20 | 40% | 65% | 0.93 | 0.45 | 8 / 5 / 0 / 0 / 7 | 0 / 8 / 12 |
| multi_family SE.06 | 20 | 30% | 45% | 0.79 | 0.49 | 4 / 3 / 2 / 0 / 11 | 0 / 6 / 14 |
| multi_family SE.07 | 20 | — | 10% | 0.36 | — | 0 / 0 / 0 / 2 / 18 | 1 / 0 / 19 |
| office SE.01 | 20 | 65% | 25% | 1.31 | 0.37 | 3 / 1 / 1 / 0 / 15 | 2 / 13 / 5 |
| office SE.02 | 20 | 45% | 35% | 0.99 | 0.33 | 4 / 2 / 1 / 0 / 13 | 1 / 9 / 10 |
| office SE.03 | 20 | 25% | 45% | 0.88 | 0.33 | 7 / 2 / 0 / 0 / 11 | 1 / 5 / 14 |
| office SE.04 | 20 | 20% | 45% | 0.77 | 0.33 | 7 / 2 / 0 / 0 / 11 | 1 / 4 / 15 |
| office SE.05 | 20 | 20% | 25% | 0.58 | 0.19 | 3 / 0 / 2 / 0 / 15 | 0 / 4 / 16 |
| office SE.06 | 20 | 15% | 25% | 0.59 | 0.26 | 2 / 1 / 2 / 0 / 15 | 2 / 3 / 15 |
| office SE.07 | 5* | — | 0% | 0.24 | — | 0 / 0 / 0 / 0 / 5 | 0 / 0 / 5 |
| school SE.01 | 20 | 70% | 55% | 1.35 | 0.47 | 8 / 2 / 1 / 0 / 9 | 2 / 14 / 4 |
| school SE.02 | 20 | 70% | 70% | 1.33 | 0.71 | 6 / 5 / 3 / 0 / 6 | 4 / 14 / 2 |
| school SE.03 | 20 | 60% | 90% | 1.27 | 0.72 | 6 / 8 / 4 / 0 / 2 | 3 / 12 / 5 |
| school SE.04 | 20 | 35% | 80% | 1.10 | 0.66 | 10 / 3 / 3 / 0 / 4 | 5 / 7 / 8 |
| school SE.05 | 20 | 40% | 65% | 0.95 | 0.54 | 7 / 1 / 5 / 0 / 7 | 0 / 8 / 12 |
| school SE.06 | 20 | 30% | 60% | 0.98 | 0.63 | 6 / 4 / 2 / 0 / 8 | 3 / 6 / 11 |
| school SE.07 | 18 | — | 44% | 0.82 | — | 0 / 0 / 0 / 8 / 10 | 4 / 0 / 14 |

The by-type, by-carrier and overall rows are in [`tables.md`](results_national/tables.md).

## How the sample was drawn

| Item | Value |
| --- | --- |
| Source | epsm_db GIS lake (`epsm_lake`, publication revision 10978, schema 2), read through your `ssanjay` reader role |
| Frame | `gis.model_export_buildings`: single-building EPC, valid footprint ≥ 100 m², a register construction year, and lake building type single-family / multifamily / office / school. Era comes from the register year. |
| Order | `md5(seed ‖ building id)` within each type × era, with seed `catalogue-validation-2026-10-26`; the first 20 that pass the screens are kept |
| Screens | Same as Uddevalla: the lake EPC heating target (`epsm_db.epc_heating`, the same logic) with a measured twelve-month period and a single carrier; model assembly with compile preflight; model carrier = EPC carrier; runner era = frame era |
| Source function | The lake's own `building_type`: register purposes, complementary buildings excluded, school and office also from an EPC Atemp share ≥ 50 %. The Uddevalla label screen is not reapplied, because the lake does not parse `Samhällsfunktion` purposes into `purposes`. |
| Screened | 1,231 candidates for 543 kept. Exclusions: 306 calculated EPC (no measured period), 234 mixed or missing carrier, 74 height evidence, 31 EPC dated before construction, 11 other assembly or AMY-year cases, and 32 platform simulation failures (below) |
| Short cohorts | Office SE.07 has only 30 buildings in the national frame, all screened: 5 kept. School SE.07 used its whole frame of 102: 18 kept. Multifamily SE.07 needed 237 candidates. |
| Weather | smhi2epw calendar AMYs 2014–2025 at the centroid of each municipality's registered buildings: 470 AMYs in 168 municipalities. Nearest-station distance median 17 km, maximum 70 km. |
| Climate zone | `epsm_data.climate_zones.climate_zone_for_county(municipality code[:2])`: 438 Zone 3, 79 Zone 2, 26 Zone 1 |
| Model | `epsm.legacy_records.EPSMBuilding.from_record` on lake records (epsm branch `claude/lake-record-runner`, `ec6b1bb`), default `ModelPolicy()`; overrides limited to `renovation_state` and `climate_zone` |
| Simulations | 1,881 accepted EnergyPlus 24.2 runs for the 543 scored buildings (3 states, or 1 for SE.07, per measured calendar year); 13 processes; about 1.5 hours of simulation over three resumable passes |

**Platform replacements (32 buildings).** A sampled building that could not produce all
of its runs was replaced by the next candidate in the same order. Reasons:

- 10 courtyard or split ground floors that the Kiva ground model rejects
- 10 EnergyPlus warm-up non-convergence, mostly in the Advanced state only
- 7 footprint geometry faults: near-coincident vertices, pitched roofs over touching
  parts, one nonreciprocal adjacency
- 5 other EnergyPlus acceptance rejections: sliver surfaces, incomplete attic view
  factors, psychrometric warnings

Replacements cluster in offices SE.05–SE.06 (12) and older schools (8). The sample
is therefore drawn from buildings the platform can simulate, and courtyard blocks are
under-represented.

## Systematic cohort failures and suspected causes

These meet the contract's definition of a systematic cohort failure (n = 20, consistent
across neighbouring eras). The causes are suspected, not established.

1. **Offices SE.02–SE.07 underpredicted.**
   - **Evidence:** Existing median r falls from 0.99 to 0.24 with era. Match is 25–45 %,
     and measured heating is above the range in 10–16 of 20 buildings per era.
   - **Ventilation:** 116 of 125 offices have FTX, with median Existing r 0.74 and match 28 %.
   - **Range:** the bracket is extremely wide (Advanced median r 0.19–0.33), so the failure
     is at the top of the range.
   - **Suspected causes:**
     - The platform's single FTX recovery of 0.7 and fixed office ventilation hours. Real
       offices run longer and recover less; the catalogue's era FTX templates (0.60 for
       1976–2005) are not used (see limitation).
     - Internal gains too high for the measured use.
     - Existing envelopes for SE.04–SE.06 offices too efficient.
   - **Heat pumps:** offices with heat pumps are worst (median r 0.51), which also points to
     the fixed COP of 3.
2. **Multifamily SE.05–SE.07 underpredicted; SE.07 is badly low.**
   - **Evidence:** Existing median r 0.93, 0.79 and 0.36, with measured heating above the
     range in 12, 14 and 19 of 20 buildings.
   - **SE.07:** the model gives 11 kWh/m² against 34 measured. Same direction, weaker, for
     SE.02–SE.03, where half the buildings are above range.
   - **Suspected causes:**
     - A design-to-operation performance gap in new buildings (airtightness, FTX in
       operation, indoor temperatures above 21 °C).
     - Hot-water circulation losses that EPC heating includes and the model omits.
     - SE.07 airtightness and FTX 0.80 assumptions.
3. **Single-family SE.01 and SE.03 overpredicted.**
   - **Evidence:** Existing median r 1.95 and 1.80, and even Advanced is about 1.0. Measured
     heating is below the range in 10 and 11 of 20 houses, at 46–58 kWh/m² against
     85–91 kWh/m² modelled.
   - **Not just heat pumps:** single-family houses on district heat (r 1.72) and direct
     electricity (1.74) show the same thing, so the heat-pump COP is not the main cause.
   - **Suspected causes:**
     - Unrecorded secondary heating (wood stoves and fireplaces, not in EPC carriers).
     - Partly heated attics and basements that the model treats as conditioned.
     - Renovations deeper than the catalogue's Advanced state.
     - The prebound effect (lower indoor temperatures in poorly insulated homes).
4. **Single-family SE.07 overpredicted.**
   - **Evidence:** 19 of 20 measure below the single state (median r 1.30, 19 against
     28 kWh/m²).
   - **Suspected cause:** the opposite direction to new multifamily blocks, which suggests
     different single-family systems: exhaust-air or ground-source heat pumps with a
     seasonal COP above 3.
5. **Schools SE.04–SE.06 underpredicted at the top of the range.**
   - **Evidence:** match is 60–80 %, but measured heating is above the range in 8–12 of 20.
   - **Note:** older schools are the catalogue's best cohorts (SE.01–SE.03: coverage
     60–70 %, match 55–90 %).

What does not explain the failures:

- **Atemp/geometry mismatch.** Buildings failing the 0.75–1.25 area screen score about
  the same (coverage 41 %, match 53 %) as those passing (45 %, 56 %).
- **Climate zone.** Zones 1–2 are not worse than Zone 3, although n is small (105).

## Proposed issues (not applied)

**epsm_data (catalogue)**

- **C2 (from Uddevalla, now national).** Check the Existing states' era gradient against
  measured stock data before changing any value. The question is whether SE.01–SE.03
  single-family Existing is too poor and SE.05–SE.07 multifamily and office are too
  efficient. Use era-level sources such as BETSI, Boverket's EPC statistics and the
  Energimyndigheten stock surveys, not this sample.
- **C1 (from Uddevalla).** The observed-FTX mapping disagrees with its own rule for SE.03.
  Larger samples will not resolve this; it is a documentation or data fix.
- **C3.** Office Existing states for SE.04–SE.07. Revisit only after P2, because offices
  are where the platform's ventilation defaults matter most.

**epsm (platform)**

- **P1.** SE.07 without a state. Fixed on `claude/se07-single-state`; this run used it.
- **P2.** Use the catalogue's ventilation templates and facade WWR. Done on
  `claude/catalogue-templates` (`0a58c0c`); see the template rerun below.
- **P3.** Heat-pump and exhaust-air heat-pump performance, instead of a fixed COP of 3.
- **P4 (new).** Lake records. Done on `claude/lake-record-runner`: record assembly reads
  GIS-lake schema 2 natively. It gives identical models to the old database for 78 of
  the 82 Uddevalla buildings and equivalent models for the other 4.
- **P5 (new).** Courtyard and split ground floors. The Kiva ground model rejects floors
  with holes or disconnected parts (10 sampled buildings), so the platform cannot model
  courtyard blocks.
- **P6 (new).** EnergyPlus warm-up limit. epsm_core fixes the maximum at 25 days, which
  Advanced-state models with very low loads sometimes do not reach.

**epsm_db (lake)**

- **D3.** `Samhällsfunktion` purposes (such as *Skola*) are kept in `original_values` but
  not parsed into `purposes`. School classification therefore relies on the EPC Atemp
  share.
- **D4.** The lake has no register construction year for many buildings, for example
  12.7k schools. Those buildings are outside this frame.

## Rerun with the catalogue's own templates

The tables above use the record runner's version-3 defaults: WWR 0.20 for every type,
a type-default system when the EPC is silent, and one FTX recovery of 0.7 in every era
and state.

Runner policy version 4 (epsm `claude/catalogue-templates`, `0a58c0c`) uses epsm_data
instead:

- **Ventilation template:** the EPC-reported system, or the era default when unknown,
  selects the template. Recovery is 0.60 for SE.04–SE.05 and 0.75 for pre-1976 retrofits
  and SE.06; Advanced installs FTX 0.80; self-draught is fixed at 0.5 ACH.
- **Facade WWR:** 0.18 / 0.24 / 0.30 / 0.25 by type, with N/E/S/W ratios applied per
  facade.

The same 543 buildings, weather and EPC targets were rerun with nothing re-sampled.
539 completed in both runs. Four failed only under version 4: three Advanced-state
warm-up failures and one sliver window from a per-facade ratio.
Results: [`results_national_templates/`](results_national_templates/tables.md).

| Paired, 539 buildings | Platform defaults (v3) | Catalogue templates (v4) |
| --- | ---: | ---: |
| Coverage | 44 % | **54 %** |
| Match | 55 % | 51 % |
| Existing / Advanced median r | 1.08 / 0.56 | 1.11 / 0.39 |
| Measured above Existing | 241 | 232 |
| Measured below Advanced | 90 | 48 |
| Cohorts meeting both targets (SE.01–SE.06) | 4 | **7** |

| Type | Coverage v3 → v4 | Match v3 → v4 | Existing r v3 → v4 | Measured above range v3 → v4 |
| --- | ---: | ---: | ---: | ---: |
| Single-family | 44 → 63 % | 59 → 53 % | 1.33 → 1.36 | 29 → 33 |
| Multifamily | 48 → 51 % | 60 → 55 % | 0.96 → 0.95 | 77 → 75 |
| Office | 32 → 39 % | 32 → 35 % | 0.82 → 0.90 | 79 → 72 |
| School | 51 → 63 % | 67 → 59 % | 1.11 → 1.17 | 56 → 52 |

What this shows:

- **The templates mostly widen the range rather than re-centre it.** Installing FTX 0.80
  in Advanced lowers that end of the range, so old single-family houses and older schools
  are now bracketed (measured below range 90 → 48). Existing barely moves (median
  per-building change 0.996), and match falls slightly because the range is wider.
- **The dominant failure is not caused by the platform defaults.** Measured heating above
  even the Existing state is almost unchanged (241 → 232).
  - Multifamily SE.02–SE.06 are unchanged.
  - Offices improve only slightly: Existing median r rises from 0.82 to 0.90 with the
    higher office WWR and the lower recovery for 1986–2005.
  - This strengthens catalogue issue C2. The newer-era Existing states, and SE.07, are
    more efficient than the measured stock.
- **SE.07 gets worse.** FTX 0.80 replaces the runner's 0.7 or self-draught: multifamily
  SE.07 median r falls from 0.36 to 0.27, and school SE.07 match from 44 % to 6 %.
- **Fixed 0.5 ACH self-draught raises old single-family Existing.** For SE.01 the median r
  rises from 1.95 to 2.27, so the Existing state moves further from the measured houses.
  Coverage still improves because Advanced moves down more.

The version-3 tables above are kept as the baseline. Version 4 is what the catalogue
contract describes, so later runs should use it.

## Reproduce

The run needs the lake branch of epsm_db and the epsm runner branch on top of the
editable environment described in the Uddevalla report. In this run both came from
scratch worktrees.

```bash
git -C ~/GitHub/epsm_db worktree add ../epsm_db-lake origin/codex/gis-first-data-lake
```

```bash
git -C ~/GitHub/epsm worktree add ../epsm-lake claude/lake-record-runner
```

```bash
PYTHONPATH=../epsm-lake/src python validation/catalogue/national_three_state.py all --per-cohort 20 --frame-depth 600 --timeout 1800 --workers 13 --placeholder-epw <any.epw>
```

Use `service=epsm_lake` in `~/.pg_service.conf` with a matching `~/.pgpass` entry. Every
step resumes, and a rerun replaces buildings the platform cannot simulate. The
`summarize` step regenerates the results from `output/catalogue_validation/national/`,
which is not committed (4.4 GB).
