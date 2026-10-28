# Proposal: land the validated changes in epsm and epsm_core

28 October 2026. Evidence and acceptance tests: [`calibration_plan.md`](calibration_plan.md).
Every change below passed the cohort rule in epsm_data `docs/validation.md` on the
calibration sample and the disjoint hold-out sample.

**The catalogue side is done.** epsm_data `codex/lod2-catalogue` (pushed) already carries
the catalogue changes (round 2). The remaining work is in **epsm** (record runner,
`ModelPolicy`, EPC comparison) and **epsm_core** (applying the new bridge field). Until that
lands, the epsm_data values are not used by any model: the record runner still selects
Sveby normal use, and core does not read `thermal_bridge_delta_u_w_m2k`.

## Status

| Change | Types | Where | Status |
| --- | --- | --- | --- |
| Measured-use setpoint, BETSI by era (22.2–23.0 °C) | multifamily | epsm_data `measured_use_v1` (68a42cd) | landed; **epsm does not select it yet** (P3) |
| Self-draught total 0.39 ACH, net of infiltration | multifamily | epsm_data `measured_use_v1` (68a42cd) | landed as a note; **epsm must apply the netting** (P3) |
| Office ventilation 1.6 L/(s·m²), 06–20 | office | epsm_data `measured_use_v1` (68a42cd) | landed; **epsm does not select it yet** (P3) |
| TABULA thermal-bridge surcharge, absolute ΔU | office | epsm_data `envelope_performance` (2d3cabc) | landed; **core does not apply it** (P5) |
| Observed SE.03 FTX at 0.60 | all | epsm_data `ventilation_templates.json` (0b508f6) | landed |
| Record assembly from lake records, SE.07, catalogue templates | all | epsm `claude/catalogue-templates` (9b9405b, ec6b1bb, 0a58c0c) | **local branch, not pushed** (P1) |
| `VentTypFmed` by heating carrier | all | epsm `claude/catalogue-templates` (72096f8) | **local branch, not pushed** (P1) |
| Heat-pump seasonal COP 2.75 | all | epsm `ModelPolicy` | **not started** (P2) |
| Window airing, 4 kWh/m² × Fgeo | multifamily | epsm EPC comparison | **not started** (P4) |
| Hot-water circulation, 8.3 kWh/m² | multifamily | epsm EPC comparison | **not started** (P4) |

## P1. Land the record-runner branch (epsm)

Branch `claude/catalogue-templates` in `/Users/ssanjay/GitHub/epsm`, on top of `76640ac`,
local only:

| Commit | What it does |
| --- | --- |
| 9b9405b | SE.07 runs with no renovation state |
| ec6b1bb | assembles models from GIS-lake building records |
| 0a58c0c | `ModelPolicy` v4: catalogue ventilation templates and facade window ratios |
| 72096f8 | `VentTypFmed` → F with a heat-pump carrier (the COP carries the recovery), otherwise FTX at the observed-FTX effectiveness; F plus Fmed reads as Fmed |

Every validation number in the plan was produced with this code. Tests: the new mapping
test passes. 32 tests fail in the epsm `.venv` both with and without these commits, so the
failures come from that environment, not from this branch; check them in CI.

## P2. Heat-pump COP 2.75 (epsm `ModelPolicy`)

`ModelPolicy.heat_pump_cop` 3.0 → **2.75**, with `version` bumped to 5. Swedish
ground-source field SPF is 2.6–2.9 (Haglund Stignor et al. 2015; Energimyndigheten
2012–2014), and the Swedish exhaust-air mean is 2.7 (Nowacki, cited by Hesaraki & Holmberg
2013). It was accepted in stage 3 as a field-average refinement, not a fit. A modern
ground-source SPF for new houses (3.9) was tested and rejected (revision 5), so the value
does not vary by era or pump type.

## P3. Select measured use for existing-stock runs (epsm)

`_operation` in `legacy_records.py` calls `select_operating_profile(type)`, which is Sveby
normal use. For runs compared against measured energy:

1. Add `ModelPolicy.operation_standard` (`"sveby"` default, `"measured"` for stock runs).
   Pass it, with the resolved era, as
   `select_operating_profile(type, standard=..., era=...)`. Sveby stays the default, as
   epsm_data intends.
2. Apply `heating_setpoint_c_by_era`, the office `mechanical_vent_l_s_m2` and
   `operation_inputs` (start 06, 14 hours) from the returned record.
3. Self-draught netting, multifamily topology S only:
   `natural_exchange_ach = max(0.39 − envelope_infiltration_ach, 0.05)`. Convert
   infiltration to conditioned-volume ACH first. When it is given in L/(s·m²), use
   `q · Atemp · 3.6 / V`. Reference implementation: `perturbations.apply`
   (`self_draught_total_ach`).
4. Record the choice in the receipt ("measured stock operation, epsm.measured_use.v1").

Single-family and school have no adopted measured values. epsm_data returns Sveby for them
with a note, so no type branching is needed in epsm.

## P4. EPC-comparison accounting terms (epsm)

These describe what an EPC's measured heating includes, not the building, so they belong
to the comparison (epsm_data `docs/validation.md`, "Accounting terms"). Add them where epsm
compares a modelled result with an EPC target, as kWh over the measured period:

```
term = kwh_m2 · Atemp · days / 365 / (fuel efficiency | heat-pump COP | 1)
modelled = simulated heating + Σ terms           # then r = modelled / measured
```

| Term | kWh/m² Atemp per year | Applied to | Source |
| --- | --- | --- | --- |
| Window airing | 4 × Fgeo(municipality) | multifamily | Sveby *Brukarindata bostadshus* 2.0, ch. 5; BFS 2026:9 table 1 |
| Circulation losses | 25 × (1/0.75 − 1) = 8.3 | multifamily | BEN (BFS 2016:12) 3 §, table 3:1 |

- **Fgeo** for 290 municipalities is in [`fgeo.json`](fgeo.json), parsed from BFS 2026:9
  table 1. It is reference data from a regulation, so it would sit naturally in epsm_data
  beside the BEN hot-water profile, with epsm reading it from there.
- **Circulation** uses BEN's 25 kWh/m², the same basis as
  `select_dhw_profile(..., purpose="epc_normal_use")`, so it can read that value instead of
  hard-coding it.
- **Reference implementation:** `sensitivity.term_kwh`, `airing_kwh`, `vvc_kwh`.
- **Not accepted, so leave out:** single-family airing, office circulation, school airing.
  School airing is to be retested after the geometry fix (D1).

## P5. Apply the absolute bridge surcharge (epsm_core)

`EnvelopePerformance.thermal_bridge_delta_u_w_m2k` is TABULA's `delta_U_ThermalBridging`.
It is an additive U on the whole envelope area, and it belongs to the above-grade walls and
the thermal top. Core applies only `thermal_bridge_uplift_fraction`, to every bridged role.
In the study, that form was infeasible for uninsulated basement walls and slabs (197 of
1,875 runs failed). Proposed handling in the compiler:

```
A_env  = Σ area over wall, top, ground, basement_wall, basement_ceiling, glazing
H_wt   = Σ area · U over wall and top
uplift = ΔU · A_env / H_wt
wall, top ← bridge_equivalent(assembly, uplift)
```

- Areas come from the nominal quantity takeoff: net opaque faces and glazing panes, each
  counted once.
- The two fields are mutually exclusive. Raise an error when both are set, or when surface
  construction overrides are present.
- Reference implementation: `perturbations.bridge_uplift`.
- **Check:** confirm that core either applies the new field or rejects it. If it silently
  ignores it, office bridges are lost without notice.

## Acceptance once landed

Rerun the national baseline on both samples with the landed code
(`national_three_state.py run`, then `sensitivity.py` and `round2.py score`). The study's
reference implementations should be reproduced to within one building per cohort:

| | Calibration | Hold-out |
| --- | --- | --- |
| Multifamily match (BETSI by era, with airing and circulation) | 70.1 % | 68.3 % |
| Office match (stage 3 + bridges) | 54.8 % | 59.0 % |
| All buildings match (23.0 °C multifamily, before round 2) | 60 % | 61.4 % |

A larger difference means the platform and the study now disagree. Find the cause before
treating the numbers as a new baseline.

## Tested and not proposed

- Single-family BETSI setpoints and self-draught.
- Thermal bridges for housing and schools.
- A rise in as-built airtightness.
- An FTX in-use recovery change.
- An SE.07 state change.
- A modern heat-pump SPF.

The reasons are in the plan. Old single-family over-prediction follows the model
conditioning more floor than the EPC heats (round 2, section 4). That geometry fix (D1)
comes before any further single-family operating or fabric change.
