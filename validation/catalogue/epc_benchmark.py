"""National measured-heating benchmark per type × era from every eligible lake EPC.

Uses the validation's own frame (single-building EPC, valid footprint ≥ 100 m², register
construction year, lake building type) and target (``heating_target_from_raw``: the
measured twelve-month delivered space-heating carrier input), but no simulation. The
distribution per cohort is what the catalogue's states should bracket; see
``targets.md`` for the agreed quantile targets.

    python validation/catalogue/epc_benchmark.py
"""

from __future__ import annotations

import csv
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

HERE = Path(__file__).resolve().parent
SERVICE = os.environ.get("EPSM_LAKE", "service=epsm_lake")
OUT = HERE / "results_benchmark"
QUANTILES = (10, 25, 50, 75, 90)
ERA_SQL = """CASE WHEN f.construction_year <= 1960 THEN 'SE.01' WHEN f.construction_year <= 1975 THEN 'SE.02'
    WHEN f.construction_year <= 1985 THEN 'SE.03' WHEN f.construction_year <= 1995 THEN 'SE.04'
    WHEN f.construction_year <= 2005 THEN 'SE.05' WHEN f.construction_year <= 2021 THEN 'SE.06' ELSE 'SE.07' END"""


def rows():
    """One row per eligible building: its selected certificate and raw EPC fields."""
    with psycopg.connect(SERVICE, row_factory=dict_row) as connection:
        connection.execute("SET default_transaction_read_only = on")
        with connection.cursor(name="benchmark") as cursor:
            cursor.itersize = 5000
            cursor.execute(f"""
                SELECT f.building_id, f.building_type AS category, {ERA_SQL} AS era,
                       f.municipality_code, c.certificate_id, c.atemp_m2,
                       (SELECT array_agg(r.attributes) FROM gis.epc_records r WHERE r.epc_id = c.epc_id) AS records
                FROM gis.model_facts f
                JOIN gis.model_export_buildings b ON b.building_external_id = f.building_id
                JOIN gis.model_certificates c ON c.epc_id = f.selected_epc_id
                WHERE f.single_building_epc AND b.geometry_valid AND f.construction_year > 0
                  AND f.building_type IN ('single_family', 'multi_family', 'office', 'school')
                  AND ST_Area(b.geom) >= 100""")
            yield from cursor


def raw_fields(records):
    """Field -> list of distinct-row values, as the record hydration builds observations."""
    raw = defaultdict(list)
    for record in records or ():
        for field, value in record.items():
            if field.startswith("Egi") and value not in (None, ""):
                raw[field].append(value)
    return dict(raw)


def quantiles(values):
    if len(values) < 2:
        return {f"p{q}": (values[0] if values else None) for q in QUANTILES}
    cuts = statistics.quantiles(values, n=100, method="inclusive")
    return {f"p{q}": cuts[q - 1] for q in QUANTILES}


def main():
    from epsm_db.epc_heating import heating_target_from_raw

    groups = defaultdict(list)
    counts = defaultdict(lambda: defaultdict(int))
    for row in rows():
        key = (row["category"], row["era"])
        counts[key]["eligible"] += 1
        target = heating_target_from_raw(row["certificate_id"], raw_fields(row["records"]))
        if target.reported_period_heating_kwh is None:
            counts[key]["no_measured_target"] += 1
            continue
        if not row["atemp_m2"] or row["atemp_m2"] <= 0:
            counts[key]["no_atemp"] += 1
            continue
        value = target.reported_period_heating_kwh / row["atemp_m2"]
        groups[key + ("all",)].append(value)
        groups[key + (target.carrier,)].append(value)
        counts[key]["measured"] += 1
    OUT.mkdir(parents=True, exist_ok=True)
    table = []
    for (category, era, carrier), values in sorted(groups.items()):
        table.append({"category": category, "era": era, "carrier": carrier, "n": len(values),
                      **{k: round(v, 1) for k, v in quantiles(sorted(values)).items()}})
    with (OUT / "benchmark.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=table[0].keys())
        writer.writeheader()
        writer.writerows(table)
    (OUT / "benchmark.json").write_text(json.dumps({
        "source": "epsm_lake gis.model_facts/model_certificates/epc_records, read only",
        "unit": "measured twelve-month delivered space-heating carrier input per m² EPC Atemp (kWh/m²)",
        "frame": "single-building EPC, valid footprint >= 100 m², register construction year, lake building type",
        "counts": {f"{c} {e}": dict(v) for (c, e), v in sorted(counts.items())},
        "quantiles": table}, indent=1) + "\n")
    print(f"{sum(len(v) for k, v in groups.items() if k[2] == 'all')} buildings with a measured target")


if __name__ == "__main__":
    main()
