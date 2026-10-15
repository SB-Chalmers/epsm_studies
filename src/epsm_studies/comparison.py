"""Engine-independent comparison of accepted hourly energy results.

Engines own simulation and acceptance; a study owns its chosen comparison,
identities, expected calendar and interpretation. No engine imports occur here.
"""
from __future__ import annotations

import csv
import html
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from epsm_studies._logging import operation as logged_operation


def _calendar(values):
    labels = [v.isoformat() if hasattr(v, "isoformat") else str(v) for v in values]
    stamps = [datetime.fromisoformat(v) for v in labels]
    if not stamps or any(b - a != timedelta(hours=1) for a, b in zip(stamps, stamps[1:])):
        raise ValueError("Expected calendar must be nonempty, continuous and hourly")
    return labels


def compare_energy_results(
    reference, candidate, *, reference_identity, candidate_identity,
    expected_time_axis, signal="space_heating_demand_kwh",
):
    """Compare one kWh/hour signal after strict contract and accounting checks.

    Results implement Core's SimulationResult interface. Identities are explicit
    caller records with snapshot, physical-input and weather SHA256 values. The
    caller must capture each engine's actual inputs; matching labels are not
    evidence by themselves. Supply the complete intended calendar, not a result's
    observed coverage. Percent differences are undefined for a zero reference.
    No agreement threshold or claim of empirical accuracy is implied.
    Accounting tolerance is 0.1% relative or 0.001 kWh absolute, recorded in output.
    """
    identity_keys = ("building_snapshot_sha256", "physical_inputs_sha256", "weather_sha256")
    identities = (reference_identity, candidate_identity)
    for identity in identities:
        if any(not isinstance(identity.get(k), str) or len(identity[k]) != 64
               or any(c not in "0123456789abcdef" for c in identity[k]) for k in identity_keys):
            raise ValueError("Supply snapshot, physical-input and weather SHA256 identities")
    if any(reference_identity[k] != candidate_identity[k] for k in identity_keys):
        raise ValueError("Engine input identities differ")
    axis = _calendar(expected_time_axis)
    series = []
    totals = []
    for result, identity in zip((reference, candidate), identities):
        if result.diagnostics.get("accepted") is not True:
            raise ValueError("Comparison requires accepted engine results")
        for key, identity_key in (("physical_inputs_sha256", "physical_inputs_sha256"),
                                  ("building_snapshot_id", "building_snapshot_sha256"),
                                  ("building_snapshot_sha256", "building_snapshot_sha256")):
            if key in result.diagnostics and result.diagnostics[key] != identity[identity_key]:
                raise ValueError("Result diagnostics disagree with recorded inputs")
        if result.units.get(signal) != "kWh":
            raise ValueError("Comparison signal must have kWh units")
        if _calendar(result.time_axis) != axis:
            raise ValueError("Result calendar does not cover the complete expected hours")
        values = [float(v) for v in result.hourly[signal]]
        total = float(result.scalars[signal])
        if len(values) != len(axis) or not all(math.isfinite(v) for v in (*values, total)):
            raise ValueError("Hourly values and annual scalar must be complete and finite")
        if not math.isclose(math.fsum(values), total, rel_tol=.001, abs_tol=.001):
            raise ValueError("Annual scalar disagrees with hourly accounting")
        series.append(values)
        totals.append(total)
    ref, cand = series
    delta = [c - r for r, c in zip(ref, cand)]
    months = {}
    for stamp, r, c in zip(axis, ref, cand):
        row = months.setdefault(stamp[:7], {"reference_kwh": 0., "candidate_kwh": 0.})
        row["reference_kwh"] += r
        row["candidate_kwh"] += c
    mean_ref, mean_cand = math.fsum(ref) / len(axis), math.fsum(cand) / len(axis)
    covariance = math.fsum((r-mean_ref)*(c-mean_cand) for r, c in zip(ref, cand))
    variance = math.sqrt(math.fsum((r-mean_ref)**2 for r in ref)
                         * math.fsum((c-mean_cand)**2 for c in cand))
    return {
        "signal": signal, "units": "kWh", "hours": len(axis),
        "quality_checks": {"accepted_results": True, "shared_inputs": True,
            "complete_hourly_calendar": True, "finite_values": True,
            "annual_hourly_balance": True, "accounting_relative_tolerance": .001,
            "accounting_absolute_tolerance_kwh": .001},
        "inputs": {key: reference_identity[key] for key in identity_keys},
        "reference_run_id": reference.run_id, "candidate_run_id": candidate.run_id,
        "reference_kwh": totals[0], "candidate_kwh": totals[1],
        "difference_kwh": totals[1] - totals[0],
        "difference_percent": 100 * (totals[1]-totals[0]) / totals[0] if totals[0] else None,
        "reference_peak_kw": max(ref), "candidate_peak_kw": max(cand),
        "peak_difference_percent": 100 * (max(cand)-max(ref)) / max(ref) if max(ref) else None,
        "hourly_mae_kwh": math.fsum(abs(v) for v in delta) / len(axis),
        "hourly_rmse_kwh": math.sqrt(math.fsum(v*v for v in delta) / len(axis)),
        "hourly_correlation": covariance / variance if variance else None,
        "monthly": months,
        "hourly": [{"time": t, "reference_kwh": r, "candidate_kwh": c, "difference_kwh": d}
                   for t, r, c, d in zip(axis, ref, cand, delta)],
    }


@logged_operation("study.comparison.save")
def write_comparison_report(study, cases, directory, *, reference_label, candidate_label):
    """Save JSON, hourly CSV and a portable HTML report, retaining failed cases.

    A case is a mapping with ``case_id``, ``assumptions`` and either a validated
    ``comparison`` or an explicit ``error``. Failed cases never enter statistics.
    Output files are created exclusively; choose a new directory for another run.
    Study-specific runners and reusable workflow execution stay outside this module.
    """
    cases = list(cases)
    if not cases or len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Report needs nonempty, unique case identities")
    if any(("comparison" in c) == ("error" in c) for c in cases):
        raise ValueError("Each case needs a comparison or an explicit error")
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    paths = {"json": root/"comparison.json", "csv": root/"hourly.csv", "html": root/"report.html"}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Report exists; choose a new output directory")
    payload = {"schema": "epsm.engine-comparison/1", "study": study.to_dict(),
               "reference": reference_label, "candidate": candidate_label,
               "complete": all("comparison" in c for c in cases), "cases": []}
    hourly_rows = []
    for case in cases:
        saved = {**case}
        if "comparison" in case:
            saved["comparison"] = {k: v for k, v in case["comparison"].items() if k != "hourly"}
            hourly_rows.extend({"case_id": case["case_id"], **r} for r in case["comparison"]["hourly"])
        payload["cases"].append(saved)
    content = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    def e(value):
        return html.escape(str(value))

    def number(value):
        return "undefined" if value is None else f"{value:,.3f}"
    rows, details = [], []
    for case in payload["cases"]:
        name = e(case["case_id"])
        if "error" in case:
            rows.append(f'<tr><td>{name}</td><td colspan="7">FAILED: {e(case["error"])}</td></tr>')
            continue
        c = case["comparison"]
        rows.append('<tr><td>'+name+'</td>'+''.join('<td>'+number(c[k])+'</td>' for k in (
            "reference_kwh", "candidate_kwh", "difference_percent", "reference_peak_kw",
            "candidate_peak_kw", "hourly_rmse_kwh"))+f'<td>{c["hours"]:,}</td></tr>')
        monthly = ''.join('<tr><td>'+e(month)+'</td><td>'+number(v['reference_kwh'])
                          +'</td><td>'+number(v['candidate_kwh'])+'</td></tr>'
                          for month, v in c['monthly'].items())
        details.append(f'<h2>{name}</h2><p>{e(case.get("assumptions", ""))}</p>'
            f'<p>Peak difference: {number(c["peak_difference_percent"])}%. '
            f'Hourly correlation: {number(c["hourly_correlation"])}</p>'
            f'<table><tr><th>Month</th><th>{e(reference_label)} kWh</th><th>{e(candidate_label)} kWh</th></tr>'
            +monthly+'</table><details><summary>Input identities and engine treatment</summary><pre>'
            +e(json.dumps({"inputs": c["inputs"], "engine_treatment": case.get("engine_treatment")}, indent=2))
            +'</pre></details>')
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><title>'+e(study.name)+'''</title>
<style>body{font:16px/1.5 system-ui;max-width:1150px;margin:40px auto;padding:0 24px;color:#17212c}
table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:9px;border-bottom:1px solid #d9e0e8;text-align:right}
th:first-child,td:first-child{text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
h1,h2{line-height:1.2}h2{margin-top:40px}a{color:#17519a}</style><h1>'''+e(study.name)+'</h1><p>'+e(study.question)+'''</p>
<p>Positive differences mean the candidate exceeds the reference. Similar annual totals do not imply similar peaks or hourly behaviour.
These fixtures test implementation agreement; they do not establish empirical accuracy. Failed cases remain visible and are excluded from comparisons.</p>
<p>Peak kW is the maximum hourly-average power, derived from kWh over one hour; it is not an instantaneous HVAC design load.</p>
<p><a href="comparison.json">Machine-readable report</a> · <a href="hourly.csv">Hourly results</a> · <a href="protocol.json">Study protocol</a></p>
'''+('<p><strong>Incomplete: at least one case failed.</strong></p>' if not payload['complete'] else '')
    document += '<table><tr><th>Case</th><th>'+e(reference_label)+' kWh</th><th>'+e(candidate_label)+''' kWh</th>
<th>Difference %</th><th>Reference peak kW</th><th>Candidate peak kW</th><th>Hourly RMSE kWh</th><th>Hours</th></tr>'''
    document += ''.join(rows)+'</table>'+''.join(details)+'<h2>Protocol and runtime sources</h2><pre>'+e(json.dumps(study.to_dict(), indent=2))+'</pre></html>'
    study.save(root/'protocol.json')
    with paths['json'].open('x') as f:
        f.write(content)
    with paths['csv'].open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=('case_id', 'time', 'reference_kwh', 'candidate_kwh', 'difference_kwh'))
        writer.writeheader()
        writer.writerows(hourly_rows)
    with paths['html'].open('x') as f:
        f.write(document)
    return paths
