# Catalogue validation: first Uddevalla run

> A national follow-up on the epsm_db GIS lake (543 buildings, 20 per cohort) is in
> [national.md](national.md). It confirms the patterns below at cohort scale.

26 October 2026. Contract: epsm_data [`docs/validation.md`](https://github.com/SB-Chalmers/epsm_data/blob/codex/lod2-catalogue/docs/validation.md)
(catalogue `92d776d`). Runner: [`uddevalla_three_state.py`](uddevalla_three_state.py).
Generated tables: [`results/tables.md`](results/tables.md). Per-building and excluded
rows: [`results/buildings.csv`](results/buildings.csv), [`results/excluded.csv`](results/excluded.csv).
Full summary and manifest: [`results/summary.json`](results/summary.json).

## Result

| Panel, 82 buildings | Result | Provisional target |
| --- | ---: | ---: |
| Coverage: measured between Advanced and Existing | **44 %** (36 of the 81 with a range) | ≥ 70 % |
| Match: some state within ±20 % | **57 %** (47) | ≥ 50 % |
| Existing-state median r | 1.06 | reported |
| Advanced-state median r | 0.53 | reported |
| Selected state E / S / A / SE.07 / none | 25 / 18 / 4 / 0 / 35 | reported |
| Measured below / inside / above the simulated range | 9 / 36 / 37 | — |

**No cohort reaches n = 10.** The Uddevalla panel was sampled at five buildings or fewer
per type × era, so every cohort row below is flagged and none can pass or fail the
contract yet. The panel totals are reported. Schools come closest to the targets:
coverage 57 % and match 71 % over 21 buildings. Among the 11 schools whose EPC Atemp
agrees with the model geometry, coverage is 82 % and match 73 %.

The dominant failure is one-sided. In **37 of 82 buildings the measured heating exceeds
the Existing state**, even though Existing is meant to be the upper end of the bracket.
In 9, Advanced still overpredicts. The match rate is acceptable because the three
states span a wide range: the Advanced median is about half the Existing median. The
upper end of the range is too low for multifamily SE.02–SE.05, offices and school
SE.04. Standard never exceeded Existing (0 of 82). The non-monotone SE.06 states seen
in epsm_db's 14 October matrix are gone.

## Cohort table

`*` n < 10. Selected = the closest state within ±20 %; "none" = no state matched. A single
SE.07 state spans no range, so coverage is "—" there.

| Cohort | n | Coverage | Match | Existing median r | Advanced median r | Selected E / S / A / SE.07 / none | Measured below / inside / above range |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_family SE.01 | 3* | 67% | 67% | 1.29 | 0.71 | 0 / 2 / 0 / 0 / 1 | 0 / 2 / 1 |
| single_family SE.02 | 1* | 100% | 100% | 1.25 | 0.84 | 0 / 1 / 0 / 0 / 0 | 0 / 1 / 0 |
| single_family SE.03 | 2* | 100% | 100% | 1.20 | 0.65 | 1 / 1 / 0 / 0 / 0 | 0 / 2 / 0 |
| single_family SE.04 | 4* | 25% | 50% | 1.10 | 0.58 | 1 / 1 / 0 / 0 / 2 | 1 / 1 / 2 |
| single_family SE.05 | 3* | 0% | 33% | 2.71 | 1.52 | 1 / 0 / 0 / 0 / 2 | 2 / 0 / 1 |
| single_family SE.06 | 4* | 50% | 75% | 1.50 | 1.03 | 0 / 1 / 2 / 0 / 1 | 2 / 2 / 0 |
| multi_family SE.01 | 5* | 80% | 80% | 1.43 | 0.52 | 1 / 3 / 0 / 0 / 1 | 0 / 4 / 1 |
| multi_family SE.02 | 5* | 40% | 60% | 0.89 | 0.43 | 2 / 1 / 0 / 0 / 2 | 0 / 2 / 3 |
| multi_family SE.03 | 5* | 20% | 60% | 0.95 | 0.54 | 3 / 0 / 0 / 0 / 2 | 0 / 1 / 4 |
| multi_family SE.04 | 5* | 20% | 40% | 0.57 | 0.31 | 1 / 1 / 0 / 0 / 3 | 0 / 1 / 4 |
| multi_family SE.05 | 5* | 20% | 20% | 0.64 | 0.34 | 0 / 1 / 0 / 0 / 4 | 0 / 1 / 4 |
| multi_family SE.06 | 5* | 40% | 60% | 1.13 | 0.87 | 0 / 2 / 1 / 0 / 2 | 2 / 2 / 1 |
| office SE.01 | 2* | 50% | 50% | 0.87 | 0.23 | 1 / 0 / 0 / 0 / 1 | 0 / 1 / 1 |
| office SE.02 | 3* | 67% | 33% | 1.60 | 0.49 | 1 / 0 / 0 / 0 / 2 | 0 / 2 / 1 |
| office SE.03 | 4* | 25% | 25% | 0.79 | 0.28 | 1 / 0 / 0 / 0 / 3 | 0 / 1 / 3 |
| office SE.04 | 3* | 33% | 67% | 0.87 | 0.34 | 2 / 0 / 0 / 0 / 1 | 0 / 1 / 2 |
| office SE.06 | 2* | 0% | 0% | 0.54 | 0.24 | 0 / 0 / 0 / 0 / 2 | 0 / 0 / 2 |
| school SE.01 | 5* | 80% | 40% | 1.42 | 0.58 | 1 / 1 / 0 / 0 / 3 | 0 / 4 / 1 |
| school SE.02 | 5* | 60% | 100% | 1.18 | 0.63 | 3 / 1 / 1 / 0 / 0 | 1 / 3 / 1 |
| school SE.03 | 4* | 100% | 100% | 1.12 | 0.69 | 3 / 1 / 0 / 0 / 0 | 0 / 4 / 0 |
| school SE.04 | 5* | 20% | 60% | 0.97 | 0.58 | 2 / 1 / 0 / 0 / 2 | 0 / 1 / 4 |
| school SE.05 | 1* | 0% | 100% | 0.90 | 0.53 | 1 / 0 / 0 / 0 / 0 | 0 / 0 / 1 |
| school SE.07 | 1* | — | 0% | 2.87 | — | 0 / 0 / 0 / 0 / 1 | 1 / 0 / 0 |

By type (n): single-family 17, multifamily 30, office 14, school 21. By-type,
by-carrier and overall rows are in [`results/tables.md`](results/tables.md). Office
SE.05 has no comparable building.

## Run inventory

| Item | Value |
| --- | --- |
| Buildings | 107 in epsm_db's screened Uddevalla panel (source function, no complementary buildings, footprint ≥ 100 m²); **82 compared**, 25 excluded |
| Exclusions | 23 mixed or missing EPC heating carrier; 2 without a measured twelve-month period (one also mixed carrier). No building failed in simulation. |
| Target | EPC reported delivered space-heating carrier input over the exact measured twelve months (`sweden_ubem.epc_heating`): UPPV fields after v2.6 (65 buildings), carrier minus `EgiVVBered` before v2.6 (17) |
| Weather | epsm_db's checksum-checked smhi2epw calendar AMYs 2014–2025 at the Uddevalla reference point, reused unchanged; 26 measured periods cross a calendar year and use two simulations |
| Simulations | 322 accepted building × state × year runs (3 states × 107 building-years + 1 SE.07 run); one first SE.07 attempt failed and was rerun (see below) |
| Model | `epsm.legacy_records.EPSMBuilding.from_record`, default `ModelPolicy()`; only `renovation_state` and epsm_db's existing EPC construction-year rule (3 buildings) are overridden; EPC-reported ventilation as mapped by the runner (73 reported, 9 type default) |
| Database | epsm_db's PostGIS container, read-only transactions |
| Code | epsm_data `92d776d` (clean); epsm `76640ac`, epsm_core `586607c`, epsm_db `9511d4a` and epsm_lca `28a9ca9`, each with uncommitted changes from other sessions. These were installed editable; the diff hashes are in the manifest, taken when the summary was written. |
| Runtime | about 3 h on 10 threads; the runner now uses processes, which are about 60× faster because each run spends seconds in Python around EnergyPlus |

Reproduce from a venv holding those editable installs:

```bash
UBEM_DATABASE_URL='postgresql://…/sweden_ubem?options=-c%20default_transaction_read_only%3Don' python validation/catalogue/uddevalla_three_state.py --workers 10
```

## SE.07: runner shim

`EPSMBuilding.from_record` always passes `default_state="existing"` to the catalogue
resolver, which rejects SE.07 because SE.07 has one configuration. The panel's
2023 school (`eaaa9147`) therefore could not be assembled at all. The script wraps the
resolver to map that default to the single configuration (`allow_single_state_era`).
This changes nothing for other eras. The school runs as `school_se07` with r = 2.87. It
is a geometry review case, not a catalogue result: EPC Atemp is 1,500 m² against 816 m²
of model geometry, the EPC reports three storeys where the model has one, ventilation
falls back to the FTX default because the EPC lists both F and FTX, and the heat pump
COP is assumed. The runner itself is fixed on epsm branch `claude/se07-single-state`
(issue P1 below); the workaround is then a no-op and can be removed once that lands.

## Systematic cohort failures and suspected causes

None of these is a contract failure yet (n < 10). They are consistent enough across
neighbouring cohorts to be worth testing on a larger panel.

1. **Multifamily SE.04–SE.05 underpredicted** (Existing median r 0.57 / 0.64; measured
   above range in 8 of 10). District-heated buildings measure about 100 kWh/m², while
   Existing gives 50–60. Nine of ten have observed F (exhaust-only) ventilation. Suspected
   causes, in order:
   - Existing-state infiltration of 0.1 L/(s·m² Atemp) with thermal bridges "unknown"
     (not modelled) is tight for 1986–2005 multifamily stock.
   - The EPC heating figure may include hot-water circulation losses that the model
     does not represent.
   - The runner's F airflow comes from the Sveby profile, not measured flows.
   - SE.02–SE.03 multifamily show the same direction, more weakly.
2. **Offices underpredicted across eras** (Existing median 0.84, office SE.03 0.79,
   SE.06 0.54; 9 of 14 unmatched; measured above range in 9). All are FTX. The runner
   applies `ModelPolicy.ftx_recovery = 0.7` to every era and every state, and the office
   operating profile's ventilation hours are fixed. Neither comes from the catalogue's
   per-era FTX templates. The range is also very wide (Advanced median 0.28), so the
   failure is at the top of the bracket only.
3. **Single-family SE.05–SE.06 heat pumps overpredicted** (Existing median 2.71 / 1.50;
   Advanced still above the measurement for 4 of 7). Measured delivered energy is 11–28
   kWh/m². All seven have a heat pump and F ventilation, which is typically an exhaust-air
   heat pump. The model uses a fixed COP of 3 and no exhaust-heat recovery. This is a
   delivery-model issue in the platform, not a fabric issue. Multifamily heat-pump
   buildings go the other way (median 0.77), so a single COP change would not fix both.
4. **School SE.04 underpredicted** (Existing median 0.97, but measured above range in 4 of
   5). Three of those four fail the Atemp/geometry screen (ratio 0.46–0.57), so
   this is confounded by geometry.
5. **Cross-cutting confounders, not catalogue issues.**
   - 40 of 82 buildings fall outside the runner's Atemp/geometry screen of 0.75–1.25;
     36 of them are below 0.75, meaning the model geometry is far larger than the EPC
     Atemp.
   - Pre-v2.6 EPC targets, where hot water is subtracted from the combined figure, match
     less often (35 %) than post-v2.6 targets (63 %).
   - Six buildings use a generic operating-programme fallback.

## Proposed issues (not applied)

**epsm_data (catalogue)**

- **C1. Observed-FTX mapping disagrees with its own rule.** In
  `datasets/standards/ventilation_templates.json`, `observed_ftx_by_era` maps SE.03
  (1976–1985) to `FTX_075`. Its `observed_rule` text and `docs/templates.md` both say an
  observed FTX in 1976–2005 is original early recovery, 0.60. One of the two needs
  correcting.
- **C2. Review Existing-state airtightness and thermal bridges for multifamily
  SE.04–SE.05, and SE.02–SE.03.** Compare 0.1 L/(s·m²) and the unmodelled bridges
  against era-level stock evidence such as BETSI (`evidence/betsi_review`). Change them
  only if that source supports a looser Existing state. Do not fit to these buildings.
- **C3. Office Existing state.** Once P2 is done, recheck whether the Existing office
  states for SE.03–SE.06 are too efficient. Do not change anything before P2, because the
  platform does not yet use the catalogue's ventilation templates.

**epsm (platform runner)**

- **P1. Let SE.07 run without a state.** *Fixed on epsm branch `claude/se07-single-state`,
  not merged.* `EPSMBuilding.from_record` now uses SE.07's single configuration when no
  `renovation_state` is given, rejects an explicit state for SE.07, and keeps
  `"existing"` as the default for SE.01–SE.06.
- **P2. Use the catalogue's ventilation templates and window ratios** (limitation below).
- **P3. Represent exhaust-air heat pumps and stop using one fixed heat-pump COP** for
  every carrier and type.

**epsm_db / data**

- **D1. Atemp versus geometry.** About half the panel has model conditioned area far
  above EPC Atemp. Investigate how storeys, basements and attics are counted before
  using this panel for cohort conclusions.
- **D2. Panel size.** Draw at least 10 buildings per type × era. The contract cannot be
  evaluated at five or fewer.

## Limitation: platform defaults, not catalogue templates

The record runner does not consume two pieces of epsm_data's guidance:

- **Window-to-wall ratio.** It uses `ModelPolicy.wwr_by_type` = 0.20 for every type. The
  catalogue's `facade_assumptions()` gives 0.18 for single-family, 0.24 multifamily,
  0.30 office and 0.25 school, with an N/E/S/W split.
- **Ventilation.** It maps the EPC ventilation fields itself, falls back to
  `ModelPolicy.ventilation_by_type` (single-family S, multifamily F, office and school
  FTX), and builds the airflow with one FTX recovery of 0.7.
  - The catalogue's per-archetype `hvac_template` is not used: FTX 0.60/0.75/0.80 by era,
    and era defaults such as SE.03 school FT.
  - The catalogue's Advanced state installs FTX 0.80, but here Advanced keeps the
    observed system.

So this run validates the catalogue's fabric and infiltration states inside the
platform's own facade and ventilation assumptions, not the full catalogue contract
(inputs item 2). Offices, where windows and ventilation matter most, are where this
limitation most likely affects the result.

## Reference building: Fridhemsskolan smoke test not run

The contract asks for the same three-state test on the secondary school in
`evidence/fridhemsskolan_2017_school.md`, using geometry and measured heating from the
cited paper. Neither source supplies a measured annual heating value for a single
modelled building.

**PUB-611**, Mohamed Ahmed (2017), the Fridhemsskolan thesis:

- **Geometry:** floor, wall, roof and window areas per building only (Hus 1: 816.54 m²;
  Hus 2: 414.48 m²; Hus 3: 345.63 m²). There is no footprint polygon, storey count or
  building height. The construction year is unknown; 1960 and SE.02 are catalogue
  conventions.
- **Heating:** one district-heating meter for the whole nine-building school, covering
  space heating and hot water (443.83 MWh/year, 2014–2016 average). It is split to
  Hus 1–3 by area (288.6 MWh/year). The area used for that split (2,004.18 m²) does not
  match the sum of the thesis's own Table 3-2 areas (1,576.65 m²). Hot-water use is
  assumed, not measured.

**PUB-003**, Steen Englund et al. (2020), a separate Gävle secondary school:

- **Geometry is usable:** 97 × 18 m footprint, 9 m above ground, four storeys including
  a basement and an attic, 4,577 m² heated, built 1961–63, rotary FTX, district heating.
- **Measured heating is not annual:**
  - The only measured heat is radiator energy for 12 January – 5 April 2015 (78.8 MWh)
    and one unoccupied week. Both exclude the air-handling unit heating coils.
  - The annual 73 kWh/m² (332 MWh) is a simulated normal-year figure.
  - The district-heating bill covers six buildings and cannot be separated.

To run the smoke test, either an annual (or full heating-season) measured space-heating
value is needed for one building whose geometry is known, or the contract must be
extended to accept a partial-period radiator comparison, with the AHU coil heat
excluded from the model.
