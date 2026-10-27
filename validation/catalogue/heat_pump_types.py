"""Heat-pump type of each heat-pump building in the sample, from its selected EPC.

The type is the EPC heat-pump field with the largest reported electricity
(``EgiPump<type>`` with or without the ``UPPV`` suffix, kWh). Read-only through epsm_db;
the result is cached in ``heat_pump_types.json`` per sample for ``sensitivity.py``.

    python validation/catalogue/heat_pump_types.py     # VALIDATION_OUT selects the sample
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import national_three_state as national  # noqa: E402

TYPES = {"Mark": "ground", "Franluft": "exhaust_air", "LuftLuft": "air_air", "LuftVatten": "air_water"}
PATH = HERE / "heat_pump_types.json"


def pump_type(fields):
    """``fields`` {source_field: raw values} -> the type with the largest electricity, or None."""
    totals = {}
    for field, values in fields.items():
        name = field.removeprefix("EgiPump").removesuffix("UPPV")
        if not field.startswith("EgiPump") or name not in TYPES:
            continue
        try:
            totals[TYPES[name]] = totals.get(TYPES[name], 0.0) + float(str(values[0]).replace(",", "."))
        except (TypeError, ValueError, IndexError):
            continue
    totals = {k: v for k, v in totals.items() if v > 0}
    return max(totals, key=totals.get) if totals else None


def main():
    from epsm_db import Database

    db = Database(national.SERVICE)
    found = {}
    for b in national.kept_buildings():
        if b["carrier"] != "heat_pump":
            continue
        record = db.record(b["building_id"])
        certificate = record.selected_certificate["certificate_id"]
        fields = {o["source_field"]: o["raw_values"] for o in record.observations if o["certificate_id"] == certificate}
        found[b["building_id"]] = pump_type(fields)
    cache = json.loads(PATH.read_text()) if PATH.exists() else {}
    cache[national.OUT.name] = dict(sorted(found.items()))
    PATH.write_text(json.dumps(cache, indent=1) + "\n")
    counts = {}
    for t in found.values():
        counts[t] = counts.get(t, 0) + 1
    print(national.OUT.name, len(found), counts)


if __name__ == "__main__":
    main()
