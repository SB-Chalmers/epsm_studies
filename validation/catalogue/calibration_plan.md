# Improving the catalogue without fitting the stock

27 October 2026. Stages 1–2 of the plan agreed after the
[national run](national.md): fix the targets and the evidence before any parameter is
changed, then choose a small set of genuinely uncertain parameters with published
ranges. Stages 3 (sensitivity runs and fitting) and 4 (acceptance on the hold-out sample)
are reported in [Stage 3 results](#stage-3-results). [Round 2](#round-2-sourced-templates-for-the-catalogue-28-october)
settles the values that went into epsm_data on the `codex/lod2-catalogue` branch.

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
   the heat loss grows as insulation improves, matching the newer-era gap. Tested below
   with the Swedish TABULA ΔU_tb allowance; accepted for offices only.
2. **As-built airtightness and in-operation FTX recovery for SE.04–SE.07** (#3, #4), from
   field studies. Reviewed below: neither supports a change. The Sveby airing allowance
   found on the way is accepted for multifamily.
3. **A review of the SE.07 state.** Reviewed below: no state change; single-family
   points to heat-pump SPF, the rest to the new-building energy gap. A sourced modern
   ground-source SPF is rejected (revision 5); exhaust-air pumps have no sourced change.
4. **Circulation losses (#5).** BEN confirms they are in measured heating; accepted for
   multifamily (revision 4).
5. **An energy-signature check** if metered monthly or hourly heat is available (district
   heating). The slope against outdoor temperature separates fabric and ventilation loss
   from setpoint and constant losses, which annual EPCs cannot.

None of the accepted changes is in epsm_data or epsm yet. They live in this study
(`perturbations.py`, `sensitivity.py`) and are proposals:

| Accepted change | Types | Belongs in |
|---|---|---|
| Measured-use setpoint and ventilation values (stage 3) | multifamily, office | epsm_data operating profiles and ventilation templates |
| Thermal-bridge surcharge (revision 1) | office | epsm_data archetype states (`thermal_bridge_uplift_fraction` or adjusted assemblies) |
| Heat-pump COP 2.75 (stage 3) | all | epsm `ModelPolicy` |
| Sveby window airing (revision 3) | multifamily | epsm record runner, as an EPC-comparison term |
| Hot-water circulation losses (revision 4) | multifamily | epsm record runner, as an EPC-comparison term |

Airing and circulation describe what an EPC's measured heating includes, not the
building, so they belong with the comparison, not in the catalogue.

## Fabric revision 1: thermal bridges

The catalogue leaves `thermal_bridge_uplift_fraction` empty in every state, so the model
has no thermal-bridge loss at all. Its constructions are TABULA's nominal component layers,
and TABULA itself adds bridging as a separate envelope-wide surcharge ΔU_tb.

### Values, fixed in advance

ΔU_tb in W/(m²K) on the whole envelope area (opaque elements and glazing). Values are
from TABULA.xlsm, `Calc.Building.Set`, column `delta_U_ThermalBridging`, captured in
`tests/fixtures/residential_catalogue/tabula_operation.json`. They are the same in all
three climate zones. Nothing was fitted.

| Era | Multifamily E / S / A | Single-family E / S / A |
|---|---|---|
| SE.01, SE.02 | 0.15 / 0.15 / 0.10 | 0.15 / 0.15 / 0.11 |
| SE.03 | 0.10 / 0.10 / 0.10 | 0.10 / 0.10 / 0.10 |
| SE.04 | 0.10 / 0.10 / 0.10 | 0.10 / 0.10 / 0.06 |
| SE.05 | 0.10 / 0.10 / 0.05 | 0.10 / 0.10 / 0.00 |
| SE.06, SE.07 | 0.05 (assumed) | 0.05 (assumed) |

TABULA has no Swedish type after 2005 and no non-residential types. Two assumptions fill
the gaps:

- SE.06 and SE.07 take 0.05, the lowest non-zero Swedish TABULA value.
- Offices and schools take the multifamily value of their era and state.

**Implementation** (`perturbations.thermal_bridge_delta_u`). For each building, the added
conductance is ΔU_tb × envelope area, taken from the nominal takeoff. It is applied as an
equivalent-conductivity uplift (core's `bridge_equivalent`) on the wall and top assemblies.

Core's own uplift field applies one fraction to every bridged role, including uninsulated
basement walls and slabs. The first attempt used that field, and 197 of 1,875 runs were
infeasible. Putting the surcharge on the above-grade elements keeps the TABULA heat-loss
budget unchanged, and Kiva does not damp the ground share.

The resulting uplift is 37–90 % on wall and top U, about 15 % of a building's total U·A.

The run sits on top of the stage-3 accepted changes, and is compared against them on both
samples. Because nothing was fitted, both samples are independent tests, and a type is
accepted only if it passes the stage-3 rule on both:

- lower penalty;
- above Existing not higher;
- match not lower;
- no cohort materially worse.

### Results

Median response of simulated heating:

| State | Response |
|---|---|
| Existing | +11 to +34 % |
| Standard | +15 to +42 % |
| Advanced | +9 to +65 %, largest in SE.03–SE.04 |

The same ΔU is a much larger share of a well-insulated envelope's heat loss.

| Sample (n) | Above Existing | Below Advanced | Match | Penalty | Cohorts meeting targets |
|---|---|---|---|---|---|
| Calibration (539), accepted stage 3 | 36.4 % | 6.5 % | 56.2 % | 9.17 | 5 |
| Calibration, + bridges | 24.1 % | 16.8 % | 55.5 % | 7.90 | 8 |
| Hold-out (516), accepted stage 3 | 35.7 % | 3.6 % | 57.0 % | 6.99 | 5 |
| Hold-out, + bridges | 23.4 % | 9.0 % | 57.4 % | 4.86 | 5 |

| Type | Calibration penalty, match | Hold-out penalty, match | Decision |
|---|---|---|---|
| Office | 3.93 → 2.88, 43 → 55 % | 2.48 → 1.50, 48 → 59 % | **accepted** on both |
| Multifamily | 2.06 → 1.27, 65 → 62 % | 2.31 → 1.61, 62 → 58 % | rejected: match falls on both |
| School | 2.08 → 1.66, 62 → 61 % | 0.80 → 0.55, 64 → 59 % | rejected: match falls; SE.03 materially worse on calibration |
| Single-family | 1.10 → 2.10, 54 → 44 % | 1.40 → 1.20, 54 → 54 % | rejected: calibration penalty doubles; SE.01, SE.03, SE.06 and SE.07 materially worse |

### What this establishes

- **Above Existing.** Bridging closes about a third of the remaining overshoot above
  Existing in every type, on both samples (36 → 24 %). This is the direction stage 3 left
  open.
- **Housing and schools.** Here it overcorrects where the fabric is good or the stock is
  old. Advanced rises past measured buildings: single-family SE.01 has 60 % below Advanced
  on calibration. In multifamily SE.01–SE.02, the Existing-to-Advanced spread widens until
  measured buildings fall between states rather than near one; hold-out match drops from
  80–95 % to 50–55 %.
- **What is not supported.** The evidence does not support TABULA's Advanced-state values
  (0.10 for deep renovations of pre-1985 stock) or a flat allowance for old housing.
- **What would be overfitting.** Choosing eras or states from these results would be
  overfitting. A revision needs its own source, for example measured ψ for Swedish
  renovation details or BBR Um compliance data for SE.06/SE.07.
- **What changes.** Offices take the TABULA multifamily allowance. Housing and schools
  keep zero bridging, with the overshoot above Existing recorded as a known bias.

## How much better can match get?

`ceiling.py` scores the current model (stage-3 changes, plus office bridges) against two
oracles that see the measured values. A building matches when one state is within ±20 %
of the measured value.

- **One level.** The best single fixed intensity per cohort. It shows how much of a
  cohort one state can cover at all.
- **Three levels.** The best three fixed intensities per cohort (one for SE.07). It shows
  how good an archetype without building-specific variation can be.
- **Scaled model.** The current simulations, with each state multiplied by its own
  per-cohort factor. It shows how far re-tuning the archetypes alone could go.

On the same buildings the oracles are chosen on, the ceilings look high, about 90 %. With
20 buildings per cohort, though, that is mostly the oracle fitting noise. The honest
ceiling places the levels and factors on the calibration sample, then scores them on the
hold-out:

| Hold-out (516) | Current | One level | Three levels, in sample | Three levels, out of sample | Scaled model, out of sample |
|---|---|---|---|---|---|
| All | 59 % | 53 % | 92 % | 72 % | 67 % |
| Single-family | 54 % | 49 % | 91 % | 64 % | 66 % |
| Multifamily | 62 % | 60 % | 91 % | 76 % | 66 % |
| Office | 59 % | 53 % | 91 % | 71 % | 68 % |
| School | 64 % | 50 % | 94 % | 77 % | 70 % |

Calibration-sample values, in sample: current 59 %, one level 54 %, three levels 89 %,
scaled model 88 %.

### What the ceiling shows

1. **The realistic headroom is about 8–13 points of match**, not 30. Archetypes fitted
   with full knowledge of 539 measured buildings reach 67–72 % on new ones; we are at
   59 % without fitting. Each cohort's out-of-sample figure is noisy (about ±10 points at
   n = 20); the type and overall figures are firmer.
2. **The headroom sits at both ends of the era range.** Hold-out match, current against
   three levels out of sample:

   | Era | Current | Out of sample | Gap |
   |---|---|---|---|
   | SE.01 | 58 % | 82 % | +25 |
   | SE.02 | 75 % | 85 % | +10 |
   | SE.03 | 67 % | 78 % | +11 |
   | SE.04 | 62 % | 56 % | −6 |
   | SE.05 | 71 % | 71 % | 0 |
   | SE.06 | 46 % | 71 % | +25 |
   | SE.07 | 18 % | 45 % | +28 |

   SE.04–SE.05 have nothing left to gain from archetype revisions. SE.06–SE.07 are where
   airtightness, FTX recovery and the SE.07 state act. SE.01 is mostly office SE.01 (35 %
   against 80 %) together with the pre-1960 housing that bridging over-heated.
3. **The model's building-to-building variation does not yet help match.** A fixed
   intensity per state matches new buildings as well as a re-scaled model does, or better
   (72 % against 67 %). Within a cohort, measured differences are driven by things the
   archetype does not know: use, renovation history, operation. Building-specific inputs
   from the record (ventilation type, heat recovery, renovation status) are the way past
   the archetype ceiling, not finer archetype parameters.
4. **The three states add little over a single level** (53 % → 59 %). Their value is in
   spanning renovation scenarios, not in matching more of today's stock.

## Revision 2: as-built airtightness (no change)

Swedish field measurements, converted to operating infiltration with the q50/20 rule per
envelope area (SBUF 12499, p. 16, eq. 1–2; Sveby background report SBUF 14302,
pp. 38–39):

| Type, era | Measured | Implied infiltration | Catalogue Existing |
|---|---|---|---|
| Multifamily SE.06 | q50 0.3–0.44 L/(s·m²), whole stairwells and one 2014 block (SBUF 12633, pp. 7–9; SBUF 13329, p. 48) | ≈ 0.02–0.03 L/(s·m²) Atemp | 0.10 L/(s·m²) Atemp |
| Single-family after 2000 | q50 ≈ 0.55 L/(s·m²), n = 65 (Zou 2010, Chalmers, fig. 5.4) | ≈ 0.11 ACH | 0.2 ACH |
| Offices and schools 2007–2011, no tightness requirement | q50 mean 0.64 L/(s·m²), n = 6 (SBUF 12499, tab. 25, p. 52) | ≈ 0.06 ACH | 0.2 ACH |
| Single-family before 1988 | n50 4.4–10 h⁻¹ by era (Kronvall & Boman 1993, ELIB, fig. 7) | 0.22–0.5 ACH | 0.2–0.4 ACH |

Envelope area per m² Atemp is taken as about 1.2 for multifamily and non-residential
buildings and about 2.7 for single-family houses.

For SE.06, the catalogue is already two to five times leakier than the measurements imply.
For older eras it is consistent with them. There is no Swedish field data for SE.04,
SE.05 or SE.07 by type, nor for non-residential buildings before 2007. The measured new
buildings are biased tight: most had tightness requirements.

The stage-3 diagnostic (infiltration × 3) has no evidential basis, so no airtightness
revision is run. The newer-era gap is not leakage.

## Revision 3: Sveby window-airing allowance (accepted for multifamily)

Sveby *Brukarindata bostadshus 2.0* (2024), ch. 5, p. 9, adds window airing to calculated
space heating:

- 4 kWh per m² Atemp per year;
- multiplied by the municipality's geographic factor Fgeo (BFS 2026:9, Tabell 1;
  `fgeo.json`, 290 municipalities);
- divided by the heating system's efficiency or COP.

Sveby notes that measured heating includes airing; the model has none. The allowance
applies to housing only: Sveby's office guide treats airing as negligible (SBUF 12116,
p. 13), and there is no school guide. It is a post-processing term, so no new simulations
were needed. It is a fixed absolute amount, so it weighs more in the newer, low-demand
eras.

| Type | Calibration penalty, above, match | Hold-out penalty, above, match | Decision |
|---|---|---|---|
| Multifamily | 2.06 → 1.85; 39 → 36 %; 65 → 67 % | 2.31 → 2.06; 41 → 37 %; 62 → 63 % | **accepted** on both |
| Single-family | 1.10 → 1.15; 20 → 16 %; 54 → 55 % | 1.40 → 1.40; 26 → 25 %; 54 → 53 % | rejected: neutral; three calibration cohorts slip just past zero penalty |

The current model now matches 60 % on both samples.

## FTX in-use recovery (not run)

The model uses observed-FTX recovery of 0.60 for SE.04–SE.05, 0.75 for SE.06, and 0.80 for
SE.07 and every Advanced state.

| Evidence | Value |
|---|---|
| Well-functioning units, supply-side temperature efficiency | 0.73–0.81 (SBUF 13015, pp. 21–27; Chalmers 2015:03, pp. 46–47) |
| Expert judgement of recovery that reaches the building | 0.60–0.70 (SP 2011:26, p. 26) |
| Units in defrost below −5 °C, a minority | 0.30–0.45 (BeBo 2022:03, pp. 11–13; SBUF 14025, p. 63) |

There is no population-level measurement, and no Sveby or Boverket in-use default. The
model's values sit inside the measured range. A lower value would rest on judgement rather
than measurement, so, as in stage 3, FTX recovery is not changed. A field survey with
n > 10 per era would change that.

## SE.07 review (no state change)

SE.07 has one state, and the catalogue calls it an *explicit representative construction,
not a verified as-built building*, with no sources. Its inputs are close to passive-house
level:

| Input | SE.07 | SE.06 |
|---|---|---|
| Wall U | 0.09–0.14 W/(m²K) | 0.16–0.20 W/(m²K) |
| Glazing U | 0.8–0.9 | 1.1–1.5 |
| Infiltration | about 0.025 L/(s·m²), or 0.05 ACH | — |
| FTX recovery | 0.80 | — |

The model misses SE.07 in opposite directions by type. Median simulated ÷ measured,
calibration / hold-out, current model:

| Type | Ratio | Measured | Heating |
|---|---|---|---|
| Multifamily | 0.45 / 0.52 | 34–36 kWh/m² | 16 of 20 district heat |
| Office | 0.38 (n = 5) | 25 kWh/m² | — |
| School | 0.63 | 45 kWh/m² | — |
| Single-family | 1.34 / 1.59 | 18–19 kWh/m² electricity | all heat pumps |

**Findings**

- **No component is out of line on its own.** The fabric is at about BBR level. The
  airtightness agrees with SE.06 field measurements (revision 2), and FTX 0.80 sits at the
  top of the measured in-use range.
- **Multifamily, office and school.** SBUF 14025 names the usual new-building gap without a
  population figure:
  - FTX defrost and flow imbalance;
  - circulation and duct losses;
  - large window and balcony bridges in prefab concrete;
  - commissioning and control faults;
  - heat pumps running on auxiliary heat.

  Circulation losses (revision 4) close part of the multifamily gap: SE.07 match goes from
  20 to 35 % on calibration and from 5 to 10 % on hold-out.
- **First-year effects are in the target.** Every SE.07 certificate measures the first 0–2
  operating years. BBR requires that measurement within 24 months of completion, so
  construction moisture and commissioning are included. They are not an archetype
  property, and at n = 20 there is no clear age trend.
- **Single-family has the opposite cause.** All are heat pumps:
  - 28 of 40 sampled certificates report an exhaust-air heat pump (`EgiPumpFranluftUPPV`)
    and 11 a ground-source one;
  - 31 report `VentTypFmed` (exhaust ventilation with heat recovery).

  The model divides the full heat demand by the field-average COP 2.75 (stage 3, from older
  installations). Modern low-temperature installations likely reach a higher seasonal COP.
  Revision 5 tests a sourced modern SPF; it is rejected.

**Decision.** No SE.07 state change. A change needs either as-built evidence for new
buildings by type, or a sourced new-installation heat-pump SPF for single-family houses.

**Runner note.** The record runner mapped `VentTypFmed` to plain F. For heat-pump houses
that is right: the exhaust air is the heat pump's source, and the full demand is divided by
its COP. Without a heat-pump carrier the recovery was lost; fixed below.

## Revision 4: hot-water circulation losses (accepted for multifamily)

BEN (BFS 2016:12), general advice to 3 §, says *"Förlusterna för varmvattencirkulation
inkluderas i byggnadens energianvändning för uppvärmning"*: the measured heating target
includes circulation losses. BEN also sets delivered hot water as 0.75 × (hot water +
circulation). With BEN's normal multifamily hot water of 25 kWh/m² Atemp (tabell 3:1),
circulation is 25 × (1/0.75 − 1) ≈ **8.3 kWh/m² per year**.

For offices, Sveby *Brukarindata kontor* (p. 24) gives about **3 kWh/m²** for new offices.
Single-family houses rarely have circulation, and schools have no source.

Sveby (bostäder 2.0, p. 12) does not count circulation losses as heat released to the
building, so the whole loss is added after simulation, divided by the heating system's
efficiency or COP, with no internal gain credited.

| Type | Calibration penalty, above, match | Hold-out penalty, above, match | Decision |
|---|---|---|---|
| Multifamily | 1.85 → 0.92; 36 → 23 %; 67 → 68 % | 2.06 → 1.41; 37 → 25 %; 63 → 68 % | **accepted** on both |
| Office | 2.88 → 2.73; 39 → 35 %; 54.8 → 54.0 % | 1.50 → 1.11; 36 → 30 %; 59 → 62 % | rejected: calibration match falls by one building |

No multifamily cohort is materially worse. Match by era, calibration / hold-out:

| Era | Calibration | Hold-out |
|---|---|---|
| SE.04 | 60 → 55 % | 55 → 70 % |
| SE.06 | 58 → 74 % | 60 → 80 % |
| SE.07 | 20 → 35 % | 5 → 10 % |

SE.01–SE.03 change by at most 10 points either way.

**Order matters for airing and circulation.** Airing was tested first and accepted
(revision 3). Re-tested on top of circulation losses, airing would fail on calibration
(match 69.3 → 67.9 %, two buildings) and pass on hold-out. Both are accounting terms that
the measured target includes by definition (Sveby, BEN). The joint change against the
stage-3 model passes on both samples:

| Sample | Penalty | Above Existing | Match |
|---|---|---|---|
| Calibration | 2.06 → 0.92 | 39 → 23 % | 65 → 68 % |
| Hold-out | 2.31 → 1.41 | 41 → 25 % | 62 → 68 % |

Both are kept.

**Current model**, with stage 3, office bridges, and multifamily airing and circulation:

| Sample | Match | Multifamily |
|---|---|---|
| Calibration | 60 % | — |
| Hold-out | 61 % (61.4 % after the `VentTypFmed` fix) | 68 % |

The hold-out ceiling (three levels, out of sample) is 72 % overall and 76 % for
multifamily.

## Runner fix: exhaust ventilation with recovery (`VentTypFmed`)

`VentTypFmed` is the EPC's "F med återvinning", exhaust ventilation with heat recovery,
which in practice is an exhaust-air heat pump. In both samples, 106 of 1,063 buildings
report it:

| Case | Calibration | Hold-out | Model before | Model now |
|---|---|---|---|---|
| Heat-pump heating, `VentTypFmed` alone | 49 | 51 | F, COP | F, COP (unchanged) |
| With FTX or self-draught also reported | 5 | 3 | type default (conflict) | unchanged |
| No heat-pump heating, `VentTypFmed` alone | 0 | 2 | F | FTX, observed-FTX effectiveness |

Buildings with district heating and an exhaust-air heat pump are mostly absent: the
measured target excludes mixed carriers, so the pump's electricity must be unreported
(probably counted as property electricity) for one to enter the sample. In that case the
recovered heat lowers the measured heating, which F missed. The runner
(epsm-lake 72096f8) now models those buildings as FTX at the catalogue's observed-FTX
effectiveness for the era. It also reads F plus `VentTypFmed` as `VentTypFmed` rather than
a conflict.

The two hold-out houses (single-family SE.04, one on district heat and one on direct
electricity) were re-simulated. Their Standard ratio went from 1.33 / 1.20 to 0.96 / 0.92,
and both now match. Hold-out match is 61.0 → 61.4 % (single-family 53.6 → 55.0 %). Penalty
and above-Existing are unchanged, and calibration is unaffected. The two buildings' stage-3
and bridge sensitivity runs still use the old mapping; the current model does not use them
for single-family.

## Revision 5: modern heat-pump SPF (rejected)

The SE.07 review left single-family over-prediction to the heat-pump COP: the model
divides every heat-pump building's heat demand by the field average 2.75. The pump type
comes from each building's selected EPC (`heat_pump_types.py`: the `EgiPump<type>[UPPV]`
field with the most electricity). Every heat-pump building in both samples has one.

**Single-family SE.06–SE.07 by pump type**, calibration / hold-out (n; median simulated ÷
measured at Standard, or the single SE.07 state):

| Era | Exhaust air | Ground source | Air–water |
|---|---|---|---|
| SE.06 | 10 / 14; 1.18 / 0.99 | 5 / 4; 1.09 / 1.05 | 1 / 1 |
| SE.07 | 15 / 13; 1.47 / 1.47 | 5 / 6; 1.25 / 1.83 | 0 / 1 |

**Evidence for a seasonal performance factor (SPF) by type:**

- **Exhaust air**, the majority. The Swedish installation mean is 2.7 (Nowacki, cited by
  Hesaraki & Holmberg 2013, who use it for new Stockholm houses). Energimyndigheten's
  2013 lab test of variable-speed units gave 2.2–3.0. The EU default is 2.5 (2013/114/EU,
  colder climate, a conservative floor). None supports a value above 2.75, so exhaust-air
  over-prediction in SE.07 is not a COP question.
- **Ground source.** The Swedish field SPF is 2.7–2.9 (20 houses, 2012–2014), measured on
  pumps 7–14 years old. New single-family houses in Germany measured 3.9 (WP-Effizienz,
  2005–2010) and 4.0 (WP Monitor, 2012–2013), with the pump installed with the house. The
  EU default is 3.5. No Swedish field value for new installations was found.

**Test, fixed in advance:** SPF 3.9 for ground-source heat pumps in single-family SE.06–SE.07,
where the pump was most likely installed with the house; other eras and types keep 2.75.
EU default 3.5 as a sensitivity.

| SPF 3.9, single-family | Penalty | Above Existing | Match |
|---|---|---|---|
| Calibration | 1.10 → 1.25 | 20 → 24 % | 53.6 → 55.0 % |
| Hold-out | 1.40 → 1.50 | 26 → 29 % | 53.6 → 54.3 % |

| Cohort, calibration / hold-out | Above Existing | Match |
|---|---|---|
| SE.06 | 15 → 25 % / 40 → 50 % | 60 → 65 % / 45 → 35 % |
| SE.07 | 10 → 25 % / 15 → 20 % | 25 → 30 % / 20 → 35 % |

**Rejected on both samples**; hold-out SE.06 is materially worse. SPF 3.5 is also rejected
on both (calibration penalty 1.10 → 1.20, hold-out 1.40 → 1.50).

**What this shows.** The ground-source houses are not uniformly over-predicted: the
median is above 1, but enough of them already sit at or below Existing that a higher SPF
pushes them out of range. The over-prediction is spread across buildings, not a level. The
larger SE.07 group, exhaust-air houses, has no sourced reason for a higher COP. The
single-family new-house gap stays open; a building-level heat-pump input (the EPC's pump
type and installation year) belongs to mode 1, not to the generic archetype.

The pump-type lookup and `with_spf` stay in `sensitivity.py` for later tests. `SPF_ACCEPTED`
is empty, so the current model is unchanged.

## Round 2: sourced templates for the catalogue (28 October)

Code: [`round2.py`](round2.py). Results: [`results_round2/`](results_round2/). Four questions
left open by the revisions above, each fixed before scoring. Direct runs used the
baseline's exact environment (epsm_data `92d776d`, epsm `0a58c0c`, epsm_core `586607c` with
the same diff hash, epsm_db `db58f8a`), so only the tested value differs.

### 1. Setpoint by era, not one fitted value

Stage 3 fitted multifamily at 23.0 °C, the top of BETSI's range. BETSI reports the measured
mean by construction year (Boverket 2010, table 3.3 p. 62 and table 3.6 p. 66):

| BETSI class | Era | Single-family °C | Multifamily °C |
| --- | --- | ---: | ---: |
| -1960 | SE.01 | 20.8 | 22.2 |
| 1961–75 | SE.02 | 21.3 | 22.6 |
| 1976–85 | SE.03 | 21.7 | 22.5 |
| 1986–95 | SE.04 | 21.4 | 22.4 |
| 1996–2005 | SE.05 | 21.9 | 23.0 |

SE.06 and SE.07 take the newest class (the stock mean as a sensitivity). Multifamily per-era
values were rerun directly on both samples (888 model-years, none failed), against the
current model with 23.0 °C:

| Sample | Penalty | Above Existing | Match | Cohorts meeting targets |
| --- | --- | --- | --- | --- |
| Calibration | 0.92 → 1.02 | 23 → 24 % | 67.9 → 70.1 % | 5 → 4 |
| Hold-out | 1.41 → 1.46 | 25 → 26 % | 67.6 → 68.3 % | 3 → 3 |

The difference is two buildings on calibration (multifamily SE.03 above Existing) and one on
hold-out (SE.04). By the stage-1 rule the per-era table is not an improvement on 23.0 °C; it
is also not measurably worse, and 23.0 °C contradicts BETSI for every class before 1996.
**Decision: the catalogue takes BETSI by era.** When the sample cannot separate two values,
the sourced one is kept over the one fitted to the range edge.

Single-family per-era values, estimated linearly from the stage-3 setpoint run on
calibration, leave the penalty unchanged (1.10 → 1.10) and drop the cohorts meeting targets
from 3 to 0; with the BETSI 0.40 ACH self-draught as well, single-family SE.02 gets materially
worse. **Not adopted.** Section 4 explains why single-family should not be judged on
operation yet.

### 2. Hot-water basis for circulation losses

Revision 4 derived 8.3 kWh/m² from BEN's 25 kWh/m², while the simulation's Sveby profile
uses 21. epsm_data already separates the two purposes: `select_dhw_profile(...,
purpose="epc_normal_use")` returns BEN's 25 for EPC comparisons. Circulation on the Sveby
basis (7.0 kWh/m²) also passes on both samples but scores slightly lower (calibration
penalty 1.03 against 0.92). **Kept at 8.3 kWh/m²**, the catalogue's EPC-comparison basis.

### 3. School window airing

epsm_data's school profile records Sveby *Brukarindata undervisning* 1.0 table 2.2: 4 kWh/m²
of airing added in post-processing. The stock-wide review above had missed it.

| Sample | Penalty | Above Existing | Match |
| --- | --- | --- | --- |
| Calibration | 2.08 → 1.67 | 37 → 31 % | 62.3 → 60.9 % |
| Hold-out | 0.80 → 0.65 | 28 → 22 % | 64.2 → 64.2 % |

Match falls by two buildings on calibration, so **not accepted** by the rule, although it
passes on hold-out and per m² on both samples. It is a definitional accounting term, like
multifamily airing; it should be retested once the geometry fix in section 4 lands.

### 4. Single-family overprediction follows the area mismatch

The national run found no difference between buildings inside and outside the 0.75–1.25
Atemp/geometry screen, pooled over all types. Within single-family cohorts the relation is
strong: Existing r correlates with EPC Atemp ÷ model conditioned area at −0.38 to −0.60 in
SE.02–SE.06, and the median house conditions about a third more floor than its EPC heats.
Scaling each ratio by that factor (heating per m² of each side's own area):

| Existing median r, calibration | SE.01 | SE.02 | SE.03 | SE.04 | SE.05 | SE.06 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Single-family, total | 2.27 | 1.73 | 1.84 | 1.09 | 0.80 | 1.13 |
| Single-family, per m² | 1.62 | 1.35 | 1.63 | 0.79 | 0.67 | 0.98 |
| Multifamily, total | 1.36 | 0.97 | 1.07 | 1.16 | 0.95 | 0.80 |
| Multifamily, per m² | 0.99 | 0.79 | 0.90 | 0.89 | 0.80 | 0.64 |

Two consequences:

- **Old single-family overprediction is largely geometric.** Per m², about half of it
  disappears. The model's storey count or conditioned attic and basement exceed what the
  EPC heats (issue D1). Operating or fabric changes for old houses should wait for that fix.
- **The other types are more underpredicted than the totals show.** The accepted changes
  that raise Existing still pass per m² on both samples (all buildings: penalty 16.6 → 11.9
  calibration, 15.5 → 10.4 hold-out), so their direction holds; the remaining newer-era gap
  is larger than the total-energy tables suggest.

### Going into epsm_data

| Change | Catalogue form |
| --- | --- |
| Multifamily setpoint, BETSI by era | `select_operating_profile(..., standard="measured", era=...)` |
| Multifamily self-draught 0.39 ACH total | measured-use ventilation note; the consumer subtracts infiltration |
| Office ventilation 1.6 L/(s·m²), 06–20 | measured-use office profile |
| Office thermal bridges (revision 1) | `envelope_performance.thermal_bridge_delta_u_w_m2k` |
| Observed SE.03 FTX at 0.60 (issue C1) | `ventilation_templates.json` |

Heat-pump COP 2.75, multifamily airing and circulation stay with the platform's EPC
comparison, as described in epsm_data `docs/validation.md`.

## Sources

- TABULA.xlsm, Swedish typology, `delta_U_ThermalBridging`: <https://episcope.eu/fileadmin/tabula/public/calc/TABULA-xlsm_Download.zip>
- SBUF 12499, *Verklig lufttäthet i stora byggnader* (Blomsterberg & Burke 2012): <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/59aa6327-252a-4476-9412-f726096dadc7/FinalReport/SBUF%2012499%20Slutrapport%20Verklig%20luftt%C3%A4thet%20i%20stora%20byggnader%20-%20M%C3%A4tningar%20och%20ber%C3%A4kningar.pdf>
- SBUF 13329, *Lufttäthetens förändring i nybyggda hus* (Wahlgren et al. 2020): <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/e87a533f-4a74-4576-b28e-3a72ac7c60a6/FinalReport/SBUF%2013329%20Slutrapport%20Luftt%C3%A4thetens%20f%C3%B6r%C3%A4ndring%20i%20nybyggda%20hus%20-%20orsaker%20och%20konsekvenser%20ver20201117.pdf>
- Kronvall & Boman (1993), ELIB airtightness, 14th AIVC Conference
- BFS 2026:9, Tabell 1 (Fgeo per kommun): <https://lagen.nu/bfs/2026:9>
- SBUF 14025, *Glappet mellan projekterad och uppmätt energiprestanda* (Kempe 2021): <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/5c89c69d-b4e3-4492-bc2d-32b2ec245c8a/FinalReport/SBUF14025%20Slutrapport%20Glappet%20mellan%20projekterad%20och%20uppm%C3%A4tt%20energiprestanda.pdf>
- SBUF 13015 (Dehlin 2017), passive houses in subarctic climate: <https://vpp.sbuf.se/Public/Documents/ProjectDocuments/75be4309-a303-4285-9f5e-e4c3e85dccfe/FinalReport/SBUF%2013015%20Slutrapport%20Fungerar%20passivhusteknik%20i%20subarktiskt%20klimat%20170615.pdf>
- SP Rapport 2011:26 (Sikander, Ruud et al.): <https://www.osti.gov/etdeweb/servlets/purl/1026442>
- BeBo förstudie bostads-FTX (2022): <https://www.bebostad.se/media/6179/f%C3%B6rstudie-slutrapport-bostads-ftx.pdf>
- BFS 2016:12 (BEN), Boverkets föreskrifter om fastställande av byggnadens energianvändning vid normalt brukande: <https://lagen.nu/bfs/2016:12>
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
- Hesaraki & Holmberg (2013), *Energy performance of low temperature heating systems in five new-built Swedish dwellings*, Building and Environment 64, 85–93: <https://www.diva-portal.org/smash/get/diva2:627743/FULLTEXT01.pdf>
- Energimyndigheten field test of ground-source heat pumps, 2012–2014 (Byggkoll summary): <https://byggkoll.byggtjanst.se/artiklar/2015/november/aldre-bergvarmepumpar-haller-mattet/>
- Energimyndigheten test of variable-speed exhaust-air heat pumps (Byggkoll, 2013): <https://byggkoll.byggtjanst.se/artiklar/2013/februari/test-av-varvtalsreglerade-franluftsvarmepumpar/>
- Fraunhofer ISE, WP-Effizienz final report: <https://wp-monitoring.ise.fraunhofer.de/wp-effizienz/download/final_report_wp_effizienz_en.pdf>
- Fraunhofer ISE, WP Monitor: <https://www.ise.fraunhofer.de/en/research-projects/wp-monitor.html>
- Commission Decision 2013/114/EU, Annex Table 1 (default SPF): <https://www.legislation.gov.uk/eudn/2013/114/annexes>
