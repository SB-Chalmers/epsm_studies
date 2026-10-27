"""Stage-3 parameter changes, applied to the assembled ``BuildingSpec`` before simulation.

Each change is a type-level value from the calibration plan's shortlist, so the
catalogue (epsm_data) and the record runner (epsm) stay untouched until a change is
accepted. ``apply`` returns a new, revalidated spec, or ``None`` when no parameter
touches this building and state (the baseline run then stands).

``params`` keys (all optional):

- ``setpoint_c``: {category: heating setpoint °C} (#1; housing only in the plan)
- ``self_draught_total_ach``: {category: natural + envelope air change for topology S} (#2),
  reached by the fraction ``self_draught_weight`` {category: 0–1} of the step (default 1)
- ``infiltration_factor``: {category: factor on envelope infiltration} for the eras in
  ``infiltration_eras`` and the existing / SE.07 state only (#3)
- ``ftx_recovery_delta``: {category: added to FTX sensible recovery} (#4)
- ``vent_flow_factor``: {category: factor on the mechanical ventilation rate} (#6)
- ``vent_extra_hours``: {category: hours added before and after daily operation} (#6)
- ``heat_pump_cop``: {category: seasonal COP for heat-pump carriers} (#8)
"""

from __future__ import annotations

INFILTRATION_ERAS = ("SE.04", "SE.05", "SE.06", "SE.07")


def _revalidated(model, **changes):
    return type(model).model_validate({**model.model_dump(), **changes})


def _shift(schedule, delta):
    if schedule.periods:
        raise ValueError("Periodic setpoint schedules are not shifted")
    data = schedule.model_dump()
    for key in ("values", "weekday_values", "annual_values"):
        if data.get(key) is not None:
            data[key] = [v + delta for v in data[key]]
    return type(schedule).model_validate(data)


def _widen(schedule, hours):
    """Run each operating day ``hours`` longer at both ends, at full flow."""
    data = schedule.model_dump()
    if data.get("periods"):
        raise ValueError("Periodic ventilation schedules are not widened")
    for key in ("values", "weekday_values", "annual_values"):
        series = data.get(key)
        if series is None:
            continue
        series = list(series)
        for start in range(0, len(series), 24):
            day = series[start:start + 24]
            on = [h for h, v in enumerate(day) if v > 0]
            if not on or len(on) == 24:
                continue
            for h in list(range(max(on[0] - hours, 0), on[0])) + list(range(on[-1] + 1, min(on[-1] + 1 + hours, 24))):
                series[start + h] = 1.0
        data[key] = series
    return type(schedule).model_validate(data)


def _infiltration_ach(airflow, spec):
    if airflow.envelope_infiltration_l_s_m2 is not None:
        return airflow.envelope_infiltration_l_s_m2 * spec.load_reference_area_m2 * 3.6 / spec.geometry.conditioned_volume_m3
    return airflow.envelope_infiltration_ach or 0.0


def apply(spec, context, params):
    category, era, state = context["category"], context["era"], context["state"]
    airflow, use, changed = spec.airflow, spec.use, False

    def value(name):
        return (params.get(name) or {}).get(category)

    if (target := value("setpoint_c")) is not None:
        current = use.heating_setpoint.values[0]
        if any(v != current for v in use.heating_setpoint.values):
            raise ValueError("Non-constant heating setpoint")
        if target != current:
            use, changed = _revalidated(use, heating_setpoint=_shift(use.heating_setpoint, target - current)), True
    if (total := value("self_draught_total_ach")) is not None and airflow.topology == "S":
        natural = max(total - _infiltration_ach(airflow, spec), 0.05)
        weight = (params.get("self_draught_weight") or {}).get(category, 1.0)
        natural = airflow.natural_exchange_ach + weight * (natural - airflow.natural_exchange_ach)
        airflow, changed = _revalidated(airflow, natural_exchange_ach=natural), True
    if (factor := value("infiltration_factor")) is not None and era in INFILTRATION_ERAS and state in ("existing", None):
        field = "envelope_infiltration_l_s_m2" if airflow.envelope_infiltration_l_s_m2 is not None else "envelope_infiltration_ach"
        airflow, changed = _revalidated(airflow, **{field: getattr(airflow, field) * factor}), True
    if (delta := value("ftx_recovery_delta")) is not None and airflow.topology == "FTX":
        recovery = min(max(airflow.sensible_recovery_effectiveness + delta, 0.0), 0.95)
        airflow, changed = _revalidated(airflow, sensible_recovery_effectiveness=recovery), True
    if (factor := value("vent_flow_factor")) is not None and airflow.mechanical_vent_l_s_m2:
        airflow, changed = _revalidated(airflow, mechanical_vent_l_s_m2=airflow.mechanical_vent_l_s_m2 * factor), True
    if (hours := value("vent_extra_hours")) and airflow.mechanical_vent_l_s_m2:
        airflow, changed = _revalidated(airflow, mechanical_vent_fraction=_widen(airflow.mechanical_vent_fraction, hours)), True
    delivery = spec.delivery
    if (cop := value("heat_pump_cop")) is not None and delivery.heating and delivery.heating.carrier == "heat_pump":
        schedule = type(delivery.heating.heat_pump_cop).constant(cop)
        delivery, changed = _revalidated(delivery, heating=_revalidated(delivery.heating, heat_pump_cop=schedule)), True
    if not changed:
        return None
    return _revalidated(spec, use=use, airflow=airflow, delivery=delivery)
