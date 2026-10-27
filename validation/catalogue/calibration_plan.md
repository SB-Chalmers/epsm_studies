# Improving the catalogue without fitting the stock

27 October 2026. Stages 1–2 of the plan agreed after the
[national run](national.md): fix the targets and the evidence before any parameter is
changed, then choose a small set of genuinely uncertain parameters with published
ranges. Stages 3 (sensitivity runs and fitting) and 4 (acceptance on the hold-out sample)
are reported in [Stage 3 results](#stage-3-results). No catalogue value has been changed in
epsm_data; accepted changes are listed there for a sourced catalogue revision.

## Stage 1 — targets, fixed in advance

**Per cohort (type × era), the catalogue states should bracket measured heating:**

| Target | Tolerance | Why it is split |
| --- | --- | --- |
| Measured above the Existing state | ≤ 15 % of buildings | Existing is the top of the range |
| Measured below the Advanced state | ≤ 15 % of buildings | Advanced is the bottom of the range |
| Match (some state within ±20 %) | ≥ 50 % | Unchanged from the contract |

The two 15 % tolerances add up to the contract's 70 % coverage. Each end is tested
separately, so a failure names the state that needs work. SE.07 has a single state, so
it is judged on match and on its position in the benchmark. Standard is reported but has
no target, because the stock mixes renovation states.

**Stock-level placement.** For the whole stock, Existing should sit near the 85th
percentile of measured heating per m² and Advanced near the 15th. The benchmark
below makes this testable with every eligible EPC, not just a 20-building sample.

**What counts as an improvement.** A parameter change is accepted only if all of these
hold:

- it improves the two tolerances and match on the **hold-out sample**, not just the
  calibration sample;
- no cohort gets materially worse;
- the value stays inside its sourced range;
- it is applied per building type, or as a sourced era trend, never per cohort.

### Two independent samples

| Sample | Seed | Use |
| --- | --- | --- |
| Calibration | `catalogue-validation-2026-10-26` | The 543 buildings in [national.md](national.md); fitting happens here |
| Hold-out | `catalogue-validation-holdout-2026-10-27` | 20 per cohort, disjoint from calibration; only used to accept or reject a change |

The hold-out uses the same frame, screens, weather method and version-4 runner, with
buildings drawn in a different seeded order. Office SE.07 and school SE.07 cannot be
held out, because calibration already took every building in them that passes the
screens.

**Baseline (version-4 runner, before any change), both samples.** The hold-out run
completed with 520 buildings, 20 in each of 26 cohorts, after two passes: 34 failed runs
were replaced. Results: [`results_national_holdout/`](results_national_holdout/tables.md).

| | Calibration (539) | Hold-out (520) |
| --- | ---: | ---: |
| Measured above Existing | 43.0 % | 43.1 % |
| Measured below Advanced (SE.01–SE.06) | 6.1 % | 2.7 % |
| Match | 51 % | 54 % |
| Cohorts meeting all three targets | 4 | 5 |

The below-Advanced row first read 8.9 % and 6.3 %. Those figures wrongly counted SE.07
buildings that measure below the single SE.07 state; SE.07 has no bottom target, so the
share is taken over SE.01–SE.06 buildings only.

The failure replicates out of sample, and it is one-sided. The bottom tolerance is almost
met everywhere, while 43 % of buildings in both samples measure above the Existing state,
in the same cohorts. Stage 3 should therefore test the parameters that raise Existing:
indoor setpoint, circulation losses, airtightness and office operation. Advanced is not
the problem.

Per cohort, as above Existing / below Advanced / match (SE.07: above the single state /
— / match). "Meets targets" means ≤ 15 % / ≤ 15 % / ≥ 50 %.

| Cohort | Calibration n | above / below / match | Hold-out n | above / below / match | Meets targets (cal / hold) |
|---|---:|---|---:|---|---|
| single_family SE.01 | 20 | 0 / 25 / 70 % | 20 | 5 / 15 / 65 % | no / yes |
| single_family SE.02 | 20 | 5 / 5 / 50 % | 20 | 10 / 5 / 80 % | yes / yes |
| single_family SE.03 | 20 | 10 / 15 / 50 % | 20 | 35 / 0 / 50 % | yes / no |
| single_family SE.04 | 20 | 45 / 10 / 60 % | 20 | 35 / 5 / 50 % | no / no |
| single_family SE.05 | 20 | 60 / 5 / 35 % | 20 | 65 / 0 / 55 % | no / no |
| single_family SE.06 | 20 | 30 / 10 / 65 % | 20 | 45 / 5 / 45 % | no / no |
| single_family SE.07 | 20 | 15 / — / 40 % | 20 | 15 / — / 20 % | no / no |
| multi_family SE.01 | 20 | 5 / 0 / 75 % | 20 | 0 / 0 / 70 % | yes / yes |
| multi_family SE.02 | 19 | 58 / 0 / 79 % | 20 | 30 / 0 / 85 % | no / no |
| multi_family SE.03 | 20 | 50 / 0 / 65 % | 20 | 55 / 0 / 65 % | no / no |
| multi_family SE.04 | 20 | 45 / 10 / 55 % | 20 | 60 / 0 / 55 % | no / no |
| multi_family SE.05 | 19 | 58 / 0 / 68 % | 20 | 75 / 0 / 75 % | no / no |
| multi_family SE.06 | 19 | 68 / 0 / 47 % | 20 | 90 / 0 / 20 % | no / no |
| multi_family SE.07 | 20 | 100 / — / 0 % | 20 | 85 / — / 20 % | no / no |
| office SE.01 | 20 | 20 / 0 / 25 % | 20 | 20 / 0 / 50 % | no / no |
| office SE.02 | 20 | 40 / 5 / 45 % | 20 | 30 / 5 / 40 % | no / no |
| office SE.03 | 20 | 60 / 5 / 40 % | 20 | 55 / 0 / 60 % | no / no |
| office SE.04 | 20 | 65 / 5 / 50 % | 20 | 45 / 0 / 70 % | no / no |
| office SE.05 | 20 | 80 / 0 / 30 % | 20 | 100 / 0 / 25 % | no / no |
| office SE.06 | 19 | 74 / 11 / 32 % | 20 | 100 / 0 / 20 % | no / no |
| office SE.07 | 5 | 100 / — / 0 % | 0 | — | no / — |
| school SE.01 | 20 | 20 / 5 / 60 % | 20 | 10 / 0 / 50 % | no / yes |
| school SE.02 | 20 | 10 / 10 / 75 % | 20 | 15 / 10 / 65 % | yes / yes |
| school SE.03 | 20 | 20 / 0 / 75 % | 20 | 20 / 5 / 80 % | no / no |
| school SE.04 | 20 | 35 / 15 / 85 % | 20 | 30 / 10 / 70 % | no / no |
| school SE.05 | 20 | 35 / 0 / 65 % | 20 | 25 / 0 / 70 % | no / no |
| school SE.06 | 20 | 60 / 10 / 45 % | 20 | 65 / 5 / 50 % | no / no |
| school SE.07 | 18 | 89 / — / 6 % | 0 | — | no / — |

### National EPC benchmark

[`epc_benchmark.py`](epc_benchmark.py) applies the validation's frame and target to
every eligible EPC in the lake. **244,812 buildings** have a measured twelve-month
heating target ([`results_benchmark/`](results_benchmark/benchmark.csv); P10–P90 per
cohort and carrier). District-heated buildings measure delivered heat directly; all-carrier
figures mix in heat-pump electricity.

Catalogue placement for the district-heated sample buildings (kWh/m² Atemp, version-4
runner), against the national district-heat distribution:

| Cohort | Stock P15 | Stock P50 | Stock P85 | Model Existing median | Model Advanced median | Existing vs P85 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| multi_family SE.01 | 75 | 99 | 130 | 142 | 21 | on target |
| multi_family SE.02 | 71 | 93 | 120 | 93 | 18 | low |
| multi_family SE.03 | 65 | 89 | 120 | 88 | 19 | low |
| multi_family SE.04 | 60 | 84 | 113 | 61 | 14 | **far low** |
| multi_family SE.05 | 62 | 86 | 116 | 76 | 12 | low |
| multi_family SE.06 | 33 | 55 | 86 | 50 | 22 | low |
| multi_family SE.07 | 28 | 42 | 70 | 8 (single state) | — | **below P15** |
| office SE.01 | 62 | 97 | 141 | 145 | 28 | on target |
| office SE.02 | 53 | 82 | 124 | 94 | 22 | low |
| office SE.03 | 43 | 67 | 102 | 78 | 19 | low |
| office SE.04 | 41 | 65 | 104 | 57 | 18 | **far low** |
| office SE.05 | 39 | 65 | 102 | 46 | 13 | **far low** |
| office SE.06 | 26 | 44 | 75 | 32 | 13 | **far low** |
| office SE.07 | 20 | 38 | 50 | 6 (single state) | — | **below P15** |
| school SE.01 | 72 | 110 | 145 | 170 | 42 | on target |
| school SE.02 | 69 | 104 | 154 | 156 | 58 | on target |
| school SE.03 | 68 | 93 | 125 | 112 | 54 | near |
| school SE.04 | 63 | 88 | 124 | 108 | 50 | near |
| school SE.05 | 53 | 81 | 114 | 82 | 34 | low |
| school SE.06 | 37 | 61 | 96 | 57 | 31 | low |
| school SE.07 | 39 | 56 | 102 | 28 (single state) | — | **below P15** |

Single-family houses are rarely on district heat (1–5 per sample cohort), so their
placement is judged on per-building ratios, not on this table.

What the benchmark establishes:

1. **Measured heating falls slowly with era; the catalogue's Existing state falls fast.**
   - Older multifamily, office and school cohorts are on target.
   - From SE.02 onward, Existing drops below the stock's 85th percentile.
   - By SE.04–SE.06, offices and multifamily blocks sit near or below the stock **median**.
   - This is the stock-level version of the national run's main failure, now with
     hundreds to tens of thousands of EPCs per cohort behind it.
2. **SE.07 is far too efficient.** The single SE.07 state gives 6–28 kWh/m²; the stock's
   15th percentile is 20–39.
3. **Advanced is far below P15 everywhere.** It is a deep-renovation scenario: 12–58 kWh/m²
   against a P15 of 26–75. That makes the bottom tolerance easy to meet, but stretches the
   range so wide that match suffers. It is not a reason to change Advanced, but it should
   be reported.
4. **The samples are mostly representative.** The sample median of measured heating is
   within about 15 % of the national median in most cohorts. The exceptions are
   multifamily SE.04–SE.05 (58–60 against 76–82 kWh/m²), single-family SE.01 and school
   SE.04, which is the expected noise at n = 20.

## Stage 2 — parameters that may move, and those that may not

**Fixed:** opaque and window U-values, constructions and glazing, which are anchored to
TABULA, period building codes and product data; geometry; heated area; weather. These are
the catalogue's primary evidence, and changing them to fit EPCs would be calibration.

**Shortlist.** Each parameter is genuinely uncertain, physically meaningful, and has a
published range. Each would be applied per type, or with one sourced era trend.

| # | Parameter | Model today | Evidence range | Source | Failure it addresses | Lives in |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Indoor heating setpoint, housing | 21 °C (Sveby residential 2.0, BEN normal use) | Multifamily 22.4 °C (22.2–23.0 by era); single-family 21.2 °C (20.8–21.9) | BETSI measured, Boverket 2010, Tables 3.3 and 3.6 | Multifamily underprediction (rule of thumb: roughly 5–10 % more heating per K) | epsm_data operating profile (a measured-use variant beside Sveby normal use) |
| 2 | Self-draught air exchange | 0.5 ACH plus envelope infiltration | Measured total air change: single-family 0.40 ACH (self-draught 0.40, exhaust 0.36, supply/exhaust 0.45); multifamily 0.53 (self-draught 0.39, exhaust or FTX 0.57–0.59, supply/exhaust 0.43). Total, including infiltration | BETSI tracer gas, Boverket 2010, §4.1.2 and §4.2.2 | Old single-family overprediction | epsm_data ventilation template `S` |
| 3 | Existing-state infiltration, SE.04–SE.07 | Catalogue `envelope_performance` (for example multifamily SE.04–SE.05: 0.1 L/(s·m² Atemp)) | Weakly sourced: as-built leakage varies from below 0.1 to over 30 × the 0.8 L/(s·m²) at 50 Pa norm; no national as-built sample for new multifamily blocks was found | Chalmers 2010 thesis; SBUF täthetsprovning reports | Newer-era and SE.07 underprediction | epsm_data archetype states |
| 4 | FTX recovery in operation | 0.60 / 0.75 / 0.80 by era (template) | Rated rotary ≈ 0.80, plate 0.60–0.90; field efficiency drops with defrost and bypass. No systematic Swedish in-operation measurement was found | SLU report citing Svensk Ventilation; trade reports | Office and newer-era underprediction | epsm_data ventilation templates |
| 5 | Hot-water circulation losses in measured heating | 0 (excluded from the model; profile DHW is useful heat only) | 10–17 kWh/m² measured in multifamily VVC systems; 12–15 with pipes under the slab; default 3. **Whether EPC heating fields include them is unconfirmed** (BEN) | KTH / Energimyndigheten; RISE | Multifamily and school underprediction; a constant offset weighs most in efficient eras | Platform or epsm_data, as a heating-side loss **only if BEN confirms** |
| 6 | Office ventilation hours and flow | 1.3 L/(s·m²), 07–19, 225 days (Sveby offices 1.0) | Owners report 1.2–1.6 L/(s·m²) and 06–20 operation; Sveby table 2.2 still lists 1.5 | Sveby offices 2012 (SBUF 12116) | Office underprediction | epsm_data office profile |
| 7 | Office internal gains | 50 kWh/m²·year business electricity, 70 % as heat | Measured average 57 kWh/m²·year of business electricity (lighting 7–53, PC 1–830). The gains are not obviously too high, so lowering them is not supported | Sveby offices 2012, chapter 8 | Not an explanation; keep | — |
| 8 | Heat-pump seasonal performance | COP 3.0 | Swedish ground-source field SPF averages 2.6–2.9 (range 1.9–3.6) | Haglund Stignor et al. 2015; Stenlund & Axell | Not the cause of single-family overprediction (a lower COP would worsen it); refine to the field average only | Platform `ModelPolicy` |

**Degrees of freedom.** At most about 10 values (#1 two, #2 one, #3 two era groups,
#4 one, #5 one per sector, #6 two), fitted against 3 targets (two tolerances and match) × 27 cohorts in the
calibration sample; the hold-out sample is used only to accept or reject. Every value stays inside its published range.

**Open source gaps to close before stage 3.**

- **#5:** whether BEN counts circulation losses in the EPC's heating or hot-water
  fields. The BFS 2017:6 text could not be retrieved.
- **#3 and #4:** national as-built airtightness and in-operation FTX efficiency, for
  example from Bebo, RISE or Energimyndigheten field studies. Without them, #3 and #4
  stay wide and weak and should only be moved if the hold-out strongly supports it.

**Hypotheses the shortlist cannot fix.**

- **Unrecorded secondary heating** (wood stoves) in old single-family houses is not in
  the EPC carriers, so it cannot be modelled; it may explain part of the overprediction.
- **The SE.07 performance gap** may need more than airtightness and setpoint. If #1, #3
  and #5 together cannot bring SE.07 near the stock P15–P85, the SE.07 state itself
  needs a sourced revision.

## Stage 3 method

1. One-at-a-time sensitivity runs on the calibration sample: each parameter at the ends
   of its range, about 1.5 h per run with the version-4 runner. This gives each
   building's response.
2. Fit the type-level values to the stage-1 targets within the ranges, by linear
   interpolation of those responses.
3. Rerun calibration and hold-out at the fitted values.
4. Accept or reject each change by the rules above.

Parameters 1, 2 and 6 belong to operating profiles and templates rather than fabric, so
they can be tested as runner or profile overrides without editing epsm_data until a
change is accepted.

## Stage 3 results

28 October 2026. Code: [`sensitivity.py`](sensitivity.py) (runs, fit, comparison) and
[`perturbations.py`](perturbations.py), which applies each parameter to the assembled model
before simulation, so epsm and epsm_data are unchanged. Results:
[`results_sensitivity/`](results_sensitivity/).

### What was run

Each run moved one parameter to the far end of its evidence range, on the same calibration
buildings, states, years and AMYs as the version-4 baseline. In total there were 4,849
model-years: 3,365 simulated and 1,484 not applicable (the parameter does not touch that
building or state), with no failures. The heat-pump COP (#8) scales carrier input exactly,
so it needed no runs.

| Run | Parameter end | Types | Median change in Existing heating |
| --- | --- | --- | --- |
| `setpoint_housing` | multifamily 23.0 °C, single-family 21.9 °C (from 21) | housing | single-family +7 to +8 %; multifamily +15 to +18 %, SE.07 +31 % |
| `self_draught` | total air change 0.40 (single-family) / 0.39 ACH (multifamily) for topology S, from 0.5 ACH + infiltration (about 0.7–0.8) | housing | −26 % in the S buildings (mostly SE.01–SE.03) |
| `office_flow` | 1.6 L/(s·m²) (from 1.3) | office | +3 % (SE.01–03), +6 % (SE.04–06), +11 % (SE.07) |
| `office_hours` | 06–20 (from 07–19) | office | +3 %, +6 %, +15 % |
| `infiltration_new` (diagnostic) | envelope infiltration ×3, SE.04–SE.07, Existing / single state | all | +32 to +77 % |
| `ftx_recovery` (diagnostic) | FTX sensible recovery −0.2 | all | +8 to +23 % (SE.01–06), +57 to +74 % (SE.07) |

#5 (circulation losses) was not run until BEN is confirmed. #7 is kept as it is.

### Fit

Within each type, a grid search over the sourced ranges minimises the summed stage-1
shortfall per cohort (above Existing beyond 15 %, below Advanced beyond 15 %, match below
50 %). Each building's state results are combined linearly from its responses. Ties go to
the smallest change. The office ventilation hours are restricted to whole hours.

| Type | Fitted values | At a range end? |
| --- | --- | --- |
| multi_family | setpoint 23.0 °C; self-draught at the BETSI 0.39 ACH | setpoint at the top of 22.2–23.0 |
| single_family | setpoint 21.1 °C; self-draught 60 % of the way to 0.40 ACH | no |
| office | 1.6 L/(s·m²); 06–20 | both at the top |
| school | nothing to fit | — |
| all | heat-pump COP 2.75 (field SPF 2.6–2.9; a refinement, not fitted) | — |

**The linear combination predicts the direct rerun.** On the calibration sample, the fit
predicted 36.0 % above Existing and 57.3 % match; rerunning the models at the fitted values
gave 36.4 % and 57.5 %.

### Acceptance on the hold-out sample

The fitted values were rerun on the hold-out sample (1,875 model-years). Four Advanced-state
runs failed EnergyPlus warm-up convergence. All four had passed at baseline, so the higher
setpoint in very efficient buildings is the likely trigger. Those four buildings are left
out of the comparison (n = 516). Rules from stage 1: the type's shortfall must fall, above
Existing must not rise, match must not fall, and no cohort may get materially worse (its
shortfall rising by more than two buildings in twenty).

| Change | Hold-out result | Decision |
| --- | --- | --- |
| Multifamily setpoint 23.0 °C + measured self-draught | above Existing 56 → 41 %, match 56 → 62 %, no cohort worse | **accepted** |
| Office ventilation 1.6 L/(s·m²), 06–20 | above Existing 58 → 49 %, match 44 → 48 %; SE.05–SE.06 improve strongly, SE.01–SE.03 lose 10–15 points of match (within the materiality rule) | **accepted**, with the older-era caveat |
| Single-family setpoint 21.1 °C + 60 % self-draught | shortfall 1.55 → 1.50, but the COP alone gives 1.40; SE.01 and SE.02 lose their targets | **rejected**: no gain beyond the COP |
| Heat-pump COP 2.75 | single-family above Existing 30 → 26 %; office, school and multifamily neutral to slightly better; single-family SE.01 below Advanced 15 → 25 % (at the materiality limit) | **accepted** as the field-average refinement |

**The accepted changes, both samples** (above Existing / below Advanced SE.01–06 / match /
cohorts meeting all targets):

| | Calibration before | Calibration after | Hold-out before | Hold-out after |
| --- | --- | --- | --- | --- |
| All buildings | 43.0 / 6.1 / 51.2 % / 4 | 36.4 / 6.5 / 56.2 % / 5 | 42.8 / 2.7 / 54.3 % / 5 | 35.7 / 3.6 / 57.0 % / 5 |

Per cohort, as above / below / match, ✓ = meets all targets:

| Cohort | Calibration before | Calibration after | Hold-out before | Hold-out after |
|---|---|---|---|---|
| multi_family SE.01 | 5 % / 0 % / 75 % ✓ | 10 % / 0 % / 90 % ✓ | 0 % / 0 % / 70 % ✓ | 10 % / 0 % / 80 % ✓ |
| multi_family SE.02 | 58 % / 0 % / 79 % | 21 % / 0 % / 95 % | 30 % / 0 % / 85 % | 15 % / 0 % / 95 % ✓ |
| multi_family SE.03 | 50 % / 0 % / 65 % | 25 % / 0 % / 75 % | 53 % / 0 % / 68 % | 26 % / 0 % / 74 % |
| multi_family SE.04 | 45 % / 10 % / 55 % | 30 % / 10 % / 60 % | 60 % / 0 % / 55 % | 50 % / 0 % / 50 % |
| multi_family SE.05 | 58 % / 0 % / 68 % | 37 % / 0 % / 63 % | 75 % / 0 % / 75 % | 30 % / 0 % / 80 % |
| multi_family SE.06 | 68 % / 0 % / 47 % | 53 % / 0 % / 53 % | 90 % / 0 % / 20 % | 80 % / 0 % / 40 % |
| multi_family SE.07 | 100 % / — / 0 % | 100 % / — / 20 % | 85 % / — / 20 % | 75 % / — / 15 % |
| office SE.01 | 20 % / 0 % / 25 % | 15 % / 0 % / 30 % | 20 % / 0 % / 50 % | 15 % / 0 % / 40 % |
| office SE.02 | 40 % / 5 % / 45 % | 35 % / 5 % / 60 % | 30 % / 5 % / 40 % | 30 % / 5 % / 30 % |
| office SE.03 | 60 % / 5 % / 40 % | 40 % / 5 % / 45 % | 55 % / 0 % / 60 % | 45 % / 0 % / 45 % |
| office SE.04 | 65 % / 5 % / 50 % | 55 % / 5 % / 60 % | 47 % / 0 % / 68 % | 37 % / 5 % / 74 % |
| office SE.05 | 80 % / 0 % / 30 % | 75 % / 0 % / 50 % | 100 % / 0 % / 26 % | 89 % / 0 % / 58 % |
| office SE.06 | 74 % / 11 % / 32 % | 74 % / 16 % / 21 % | 100 % / 0 % / 21 % | 79 % / 0 % / 42 % |
| office SE.07 | 100 % / — / 0 % | 100 % / — / 0 % | — | — |
| school SE.01 | 20 % / 5 % / 60 % | 20 % / 5 % / 60 % | 10 % / 0 % / 50 % ✓ | 10 % / 0 % / 50 % ✓ |
| school SE.02 | 10 % / 10 % / 75 % ✓ | 10 % / 10 % / 75 % ✓ | 15 % / 10 % / 65 % ✓ | 15 % / 10 % / 65 % ✓ |
| school SE.03 | 20 % / 0 % / 75 % | 20 % / 0 % / 75 % | 20 % / 5 % / 80 % | 20 % / 5 % / 80 % |
| school SE.04 | 35 % / 15 % / 85 % | 30 % / 15 % / 90 % | 30 % / 10 % / 70 % | 30 % / 10 % / 70 % |
| school SE.05 | 35 % / 0 % / 65 % | 35 % / 0 % / 70 % | 25 % / 0 % / 70 % | 25 % / 0 % / 70 % |
| school SE.06 | 60 % / 10 % / 45 % | 60 % / 10 % / 55 % | 65 % / 5 % / 50 % | 65 % / 5 % / 50 % |
| school SE.07 | 89 % / — / 6 % | 89 % / — / 6 % | — | — |
| single_family SE.01 | 0 % / 25 % / 70 % | 0 % / 30 % / 70 % | 5 % / 15 % / 65 % ✓ | 5 % / 25 % / 65 % |
| single_family SE.02 | 5 % / 5 % / 50 % ✓ | 5 % / 5 % / 50 % ✓ | 10 % / 5 % / 80 % ✓ | 10 % / 10 % / 75 % ✓ |
| single_family SE.03 | 10 % / 15 % / 50 % ✓ | 10 % / 15 % / 55 % ✓ | 35 % / 0 % / 50 % | 25 % / 0 % / 55 % |
| single_family SE.04 | 45 % / 10 % / 60 % | 40 % / 10 % / 60 % | 35 % / 5 % / 50 % | 35 % / 5 % / 50 % |
| single_family SE.05 | 60 % / 5 % / 35 % | 60 % / 5 % / 55 % | 65 % / 0 % / 55 % | 55 % / 0 % / 65 % |
| single_family SE.06 | 30 % / 10 % / 65 % | 15 % / 10 % / 60 % ✓ | 45 % / 5 % / 45 % | 40 % / 5 % / 45 % |
| single_family SE.07 | 15 % / — / 40 % | 10 % / — / 25 % | 15 % / — / 20 % | 15 % / — / 20 % |

### What stage 3 establishes

1. **The sourced operating parameters close about a quarter of the gap.** Above Existing
   falls by 7 points in both samples, to about 36 %, against a target of 15 %. Match rises
   above 50 % overall, but only 5 cohorts in each sample meet all three targets.
2. **The fit is pinned to the evidence bounds.** The multifamily setpoint and both office
   parameters land at the top of their ranges. The remaining gap cannot be closed by
   operating assumptions without leaving the evidence.
3. **The gap is an era gradient that operating parameters do not have.** The improvement is
   largest where the change is largest in kWh (multifamily SE.02–SE.05). Multifamily and
   office SE.06–SE.07 and every SE.07 cohort stay far above Existing.
4. **The diagnostic levers fit that pattern.** Tripling envelope leakage in SE.04–SE.07
   would cut above Existing to 22 %; FTX recovery 0.2 lower in operation, to 27 %. Both act
   most in the newest eras. They remain weakly sourced, so neither was fitted.

### Next: sourced revisions, not fitting the fabric

Fitting U-values or constructions to EPCs would break the catalogue's purpose. Annual
heating cannot separate transmission, infiltration, ventilation recovery, setpoint and
unmodelled losses, so a fitted U-value would absorb the others and overstate the savings of
envelope renovations. The fabric stays fixed unless a revision comes from independent
evidence and passes the same hold-out test. Candidates, in order:

1. **Thermal bridges.** TABULA-style U-values often exclude linear bridging. Its share of
   the heat loss grows as insulation improves, matching the newer-era gap. A sourced
   per-era Δψ allowance (ISO 14683 defaults, Boverket guidance) is the first test.
2. **As-built airtightness and in-operation FTX recovery for SE.04–SE.07** (#3, #4), from
   field studies (RISE, Bebo, Energimyndigheten).
3. **A review of the SE.07 state.** It sits below the stock's 15th percentile, and the
   setpoint change does not fix it.
4. **Circulation losses (#5)**, once BEN's treatment is confirmed.
5. **An energy-signature check** if metered monthly or hourly heat is available (district
   heating). The slope against outdoor temperature separates fabric and ventilation loss
   from setpoint and constant losses, which annual EPCs cannot.

The accepted operating changes (the multifamily measured-use profile, office ventilation
operation, and heat-pump COP) are ready to be proposed to epsm_data and the record runner.
They are not applied yet.

## Sources

- Boverket (2010), *Energi i bebyggelsen – tekniska egenskaper och beräkningar* (BETSI): <https://www.boverket.se/globalassets/publikationer/dokument/2011/betsi-energi-i-bebyggelsen.pdf>
- Teli et al. (2018), *Indoor Temperature Variations in Swedish Households*: <https://research.chalmers.se/en/publication/507928>
- Sveby, *Brukarindata för energiberäkningar i kontor* (SBUF 12116): <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/AEDE1D22-7286-4702-9BDD-BD658A1B1186/FinalReport/SBUF%2012116%20Slutrapport%20Brukarindata%20f%C3%B6r%20energiber%C3%A4kningar%20i%20kontor.pdf>
- Sveby, *Brukarindata bostadshus 2.0* (2024): <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/e6ad8cd5-9b3d-47e8-885a-d197d7ddcc53/FinalReport/SBUF%2014302%20sltrp%20bilaga%20Sveby%20brukarindata%20bostadshus%202.0%20241111%20(5).pdf>
- KTH, *Varmvattensystem – förluster och legionella*: <https://www.kth.se/2.88189/applied-thermodynamics/projects/varmvattensystem-forluster-och-legionella-1.1357360>
- RISE, *Minskat energigap för nya flerbostadshus*: <https://ri.se/sv/nyheter/blogg/minskat-energigap-for-nya-flerbostadshus-kraver-battre-arbetssatt>
- Haglund Stignor et al., Swedish ground-source heat-pump field measurements: <https://iifiir.org/en/fridoc/field-measurements-of-ground-source-heat-pump-systems-installed-in-31303>
- Stenlund & Axell, residential ground-source field study: <https://iifiir.org/en/fridoc/residential-ground-source-heat-pump-systems-results-from-a-field-study-25014>
- Chalmers (2010) single-family airtightness thesis: <https://publications.lib.chalmers.se/records/fulltext/139940.pdf>
- SBUF 12633, *Täthetsprovning av byggnader*: <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/5cb6e41e-18e5-4381-95be-2bef41e8139e/FinalReport/SBUF%2012633%20Slutrapport%20T%C3%A4thetsprovning%20av%20byggnader,%20Etapp%202%20Metodutv%C3%A4rdering%20och%20j%C3%A4mf%C3%B6relse%20av%20metoder.pdf>
- SLU *Delrapport 6* (heat-exchanger efficiencies): <https://stud.epsilon.slu.se/21660/7/Delrapport_6.pdf>
