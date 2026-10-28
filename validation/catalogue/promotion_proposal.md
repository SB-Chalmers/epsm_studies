# Proposal: where the validated changes belong

28 October 2026, revised after a review of all EPSM repositories. Evidence and acceptance
tests: [`calibration_plan.md`](calibration_plan.md). Every change passed the cohort rule in
epsm_data `docs/validation.md` on the calibration sample and the disjoint hold-out sample.

## The ownership rules this follows

From epsm_development: `docs/terminology-and-models.md` ("Give each model one owner") and
`docs/harmonisation.md` ("Package responsibilities").

| Package | Owns | So it gets |
| --- | --- | --- |
| epsm_db | Records, observations, evidence interpretation (it already derives the EPC heating target and carrier, `epsm_db.epc_heating`) | reading EPC fields into observed systems |
| epsm_data | Sourced definitions: constructions, operating profiles, HVAC templates, envelope assumptions, factors | every sourced number |
| epsm_core | The physical Building and physical conversions, including delivery (`heating_delivery.py`) and thermal bridges (`bridge_equivalent`) | applying values physically |
| epsm | Cross-package assembly (Record + chosen definitions → Core inputs, with a report), engine dispatch, combined Results | choosing definitions and passing them through |
| epsm_workflows | Reusable experiment designs and execution; it already holds the EPC comparison boundary and unfitted cross-building metrics (`epsm_workflows.validation`) | the reusable comparison and cohort scoring |
| epsm_studies | A particular investigation: its question, samples, decisions and record | this validation study |

epsm is the UBEM platform's researcher-facing assembly layer. It should choose and connect,
not hold sourced numbers or the EPC accounting. The earlier draft put the COP, the
accounting terms and the self-draught netting in epsm. By these rules none of them belongs
there.

## Where each change belongs

| Change | Value or rule from | Applied by | Status |
| --- | --- | --- | --- |
| Measured-use setpoint by era, office ventilation | epsm_data `measured_use_v1` | epsm selects it for existing-stock runs | data landed (68a42cd); **selection missing** |
| Self-draught total 0.39 ACH, net of infiltration | epsm_data `measured_use_v1` | epsm_core, when converting the profile (it knows infiltration and volume) | data landed; **netting missing** |
| Office thermal-bridge ΔU | epsm_data `envelope_performance` | epsm adapters pass it; epsm_core applies it | data landed (2d3cabc); **silently dropped today** |
| Observed SE.03 FTX at 0.60 | epsm_data ventilation templates | epsm (template choice) | landed (0b508f6) |
| Heat-pump seasonal COP 2.75 | **epsm_data**, as a sourced heating-delivery template | epsm selects; epsm_core converts | hard-coded in epsm `ModelPolicy` (3.0) |
| EPC observed systems (ventilation type, carrier, pump type) | **epsm_db**, as interpreted observations | epsm maps them to a template | done twice: in epsm `legacy_records` and in my study scripts |
| `VentTypFmed` by carrier | rule in epsm assembly; observation from epsm_db | epsm | epsm 72096f8, local |
| Window airing, circulation losses | **epsm_data** (Sveby airing, BEN hot water, Fgeo table) | **epsm_workflows** EPC comparison | only in the study |
| Three-state cohort scoring and acceptance rule | contract in epsm_data `docs/validation.md` | **epsm_workflows** (beside `accuracy()`) | only in the study |
| Samples, tests, decisions, results | — | epsm_studies (this folder) | here |

## Work items by repository

### epsm_data

1. **Heat-pump delivery template.** A sourced heating-delivery definition with seasonal COP
   2.75, sitting next to the HVAC templates (`HVACTemplate`, `profiles.py`). Sources:
   - Swedish ground-source field SPF 2.6–2.9 (Haglund Stignor et al. 2015; Energimyndigheten 2012–2014);
   - Swedish exhaust-air mean 2.7 (Nowacki, via Hesaraki & Holmberg 2013).

   Record that a modern 3.9 was tested and rejected (revision 5), so the value is one per
   carrier. Core already validates `delivery.heating.heat_pump_cop`; a template makes the
   value inspectable and sourced. Today it is a policy constant in epsm, while
   epsm_lca's operational B6 inherits it unseen.
2. **EPC-comparison reference values**, beside `select_dhw_profile(..., purpose="epc_normal_use")`:
   - Sveby window airing, 4 kWh/m² Atemp per year;
   - the BFS 2026:9 Fgeo table ([`fgeo.json`](fgeo.json), 290 municipalities);
   - BEN's circulation share, 1/0.75 − 1 of hot water.

   These are definitions with sources, so Data holds them. Which types they apply to is the
   comparison's decision (next items).

### epsm_db

3. **Observed systems as interpreted observations**, keeping the source fields:
   - ventilation type from `VentTyp*`, conflicts kept;
   - heating carrier, with the same families `epc_heating` already uses;
   - heat-pump type from `EgiPump*`.

   epsm's `legacy_records._CARRIER_FIELDS` duplicates `epc_heating.POST_HEATING`/`PRE_HEATING`,
   and the study's [`heat_pump_types.py`](heat_pump_types.py) is a third copy. With one
   reader, the assembled model and the measured target agree by construction.

### epsm_core

4. **Absolute bridge surcharge.** Apply `thermal_bridge_delta_u_w_m2k` as a conductivity
   uplift on walls and thermal top:

   ```
   uplift = ΔU · A_env / Σ(A · U over wall and top)
   ```

   - `A_env` is the nominal takeoff over wall, top, ground, basement wall, basement ceiling and glazing.
   - The uplift field and the ΔU field are mutually exclusive.
   - Reference implementation: `perturbations.bridge_uplift`. The existing all-role uplift
     failed 197 of 1,875 runs on uninsulated basements.
5. **Self-draught netting** in profile conversion (`profile_resolution.py` or the airflow
   assembly), for a profile that gives a total air change:

   ```
   natural_exchange_ach = max(total − envelope infiltration in conditioned-volume ACH, 0.05)
   ```

   Core is the package that knows both quantities.

### epsm

6. **Pass the new fields through.** `archetypes.py` (around line 287) and
   `catalogue_application.py` (around line 190) forward only
   `thermal_bridge_uplift_fraction`. The office ΔU that epsm_data now carries is dropped
   with no error. Forward it, and report it in the application report.
7. **Select measured use** for existing-stock runs:
   - `select_operating_profile(type, standard="measured", era=...)`, behind an explicit choice;
   - Sveby stays the default, as epsm_data intends;
   - both the maintained `Building.from_record` / `apply_archetype` route and the legacy
     `ubem_v1` route in `legacy_records`.
8. **Select the delivery template** from item 1 instead of `ModelPolicy.heat_pump_cop`.
9. **Land the record-runner branch** `claude/catalogue-templates` (local, unpushed):

   | Commit | What it does |
   | --- | --- |
   | 9b9405b | SE.07 without a renovation state |
   | ec6b1bb | lake-record assembly |
   | 0a58c0c | `ModelPolicy` v4: catalogue templates and facade WWR |
   | 72096f8 | `VentTypFmed` by carrier |

   - These rules extend the legacy route. Carry them to the maintained route as it gains
     record assembly, rather than growing `legacy_records` further.
   - The carrier test in 72096f8 should read epsm_db's observation once item 3 exists.
   - Tests: the new test passes. 32 tests fail identically with and without the branch in
     the epsm `.venv`; check them in CI.

### epsm_workflows

10. **Generalise the EPC comparison boundary.** `validation.district_heat_estimate` already
    takes `airing_kwh_m2` and `net_distribution_loss_kwh_m2`, but only for district heat
    and with efficiencies. Extend it to every carrier:
    - divide by efficiency, by the seasonal COP for heat pumps, or by 1;
    - scale to the measured period (days / 365);
    - read the reference values from item 2.

    Reference implementation: `sensitivity.term_kwh`, `airing_kwh`, `vvc_kwh`.
11. **Three-state cohort scoring.** Add it next to `accuracy()`, following epsm_data
    `docs/validation.md`:
    - per building, r per state, covered and matched;
    - per cohort, above Existing, below Advanced, match, penalty;
    - the both-samples acceptance rule.

    Reference implementation: the study's `classify`, `sensitivity.score`, `overall` and `_accept`.

### epsm_studies

12. **Keep the study here:** the samples, tests fixed in advance, decisions and results. Per
    the study-archive policy, calibration protocols and fixed selections are study-specific
    and stay in Studies. Once items 10–11 exist, this study should call them instead of its
    own copies.
13. **Choose which terms apply to which type.** Airing and circulation apply to multifamily
    only; that is this study's accepted result, passed to the Workflows comparison as
    explicit inputs.

### Not affected

- epsm_rc: the delivery conversion and bridges come through the shared physical model.
- epsm_lca: inherits the delivered energy, so item 1 makes its B6 input sourced.
- epsm_studio, epsm_viewer.

## Order

1. **First, an independent fix: item 6 alone.** The office bridges are in the catalogue
   but never reach a model.
2. **Then items 1–5:** sources and physics.
3. **Then 7–9:** assembly.
4. **Then 10–11:** comparison.
5. **Last, 12:** rerun this study on the landed code and reproduce to within one building
   per cohort:

   | | Calibration | Hold-out |
   | --- | --- | --- |
   | Multifamily match (BETSI by era, with airing and circulation) | 70.1 % | 68.3 % |
   | Office match (stage 3 + bridges) | 54.8 % | 59.0 % |
   | All buildings (before round 2) | 60 % | 61.4 % |

   A larger difference means the platform and the study disagree. Find the cause before
   adopting a new baseline.

## Tested and not proposed

- Single-family BETSI setpoints and self-draught.
- Thermal bridges for housing and schools.
- Higher as-built leakage.
- An FTX in-use recovery change.
- An SE.07 state change.
- A modern heat-pump SPF.
- School airing, which is to be retested after the geometry fix.

The reasons are in the plan. Old single-family over-prediction follows the model
conditioning more floor than the EPC heats (round 2, section 4, issue D1). That fix comes
before any further single-family change.
