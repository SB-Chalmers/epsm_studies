"""Run this named fixture study; no reusable execution/cache framework lives here."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from epsm_studies import PaperStudy, compare_energy_results, write_comparison_report


def controlled_weather(path):
    """Write the explicitly synthetic 2023 release-test EPW (not climate evidence)."""
    headers = ["LOCATION,Unit test,Test,SWE,SYNTHETIC,000000,57,12,1,20",
        "DESIGN CONDITIONS,0", "TYPICAL/EXTREME PERIODS,0", "GROUND TEMPERATURES,0",
        "HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0", "COMMENTS 1,Controlled integration weather",
        "COMMENTS 2,Not measured weather", "DATA PERIODS,1,1,Data,Sunday,1/1,12/31"]
    with path.open("x") as stream:
        stream.write("\n".join(headers) + "\n")
        for hour in range(8760):
            stamp = datetime(2023, 1, 1) + timedelta(hours=hour)
            row = ["0"] * 35
            row[:10] = ["2023", str(stamp.month), str(stamp.day), str(stamp.hour+1),
                        "60", "?", "10", "5", "70", "101325"]
            row[12] = "300"
            row[20:22] = ["180", "2"]
            stream.write(",".join(row) + "\n")
    return path


def runtime_sources():
    sources = {"python": platform.python_version()}
    sources["numerical_dependencies"] = {name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "pvlib", "pydantic", "shapely")}
    for name in ("epsm_core", "epsm_rc", "epsm_data", "epsm_studies"):
        module = importlib.import_module(name)
        package = Path(module.__file__).resolve().parent
        digest = hashlib.sha256()
        for path in sorted(package.rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json"}:
                digest.update(path.relative_to(package).as_posix().encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
        record = {"version": module.__version__, "source_sha256": digest.hexdigest()}
        for parent in package.parents:
            if (parent/".git").exists():
                record["git_sha"] = subprocess.check_output(
                    ["git", "-C", str(parent), "rev-parse", "HEAD"], text=True).strip()
                record["tracked_changes"] = bool(subprocess.check_output(
                    ["git", "-C", str(parent), "status", "--porcelain", "--untracked-files=no"], text=True).strip())
                break
        sources[name] = record
    return sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", type=Path, required=True, help="Explicit complete 2023 EPW")
    parser.add_argument("--energyplus", type=Path, required=True, help="EnergyPlus 24.2 executable")
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwrite a previous study")
    args = parser.parse_args(argv)
    from shapely.geometry import Polygon
    from epsm_core import (Building, FoundationSpec, GainPartitionSpec, GeometrySpec,
                           GroundTemperatureSpec, ScheduleSpec, Weather, run_building)
    from epsm_core.compiler import EnergyPlusCompiler
    from epsm_core.weather import hourly_axis
    from epsm_rc import RCSettings, simulate_building

    # Fail before execution for missing assets; individual engine failures stay in the report.
    supplied = Weather.from_epw(args.weather.resolve(), calendar_year=2023)
    compiler = EnergyPlusCompiler(str(args.energyplus.resolve()))
    definitions_path = Path(__file__).with_name("fixtures.json")
    definitions = json.loads(definitions_path.read_text())
    sources = runtime_sources()
    sources["fixtures_sha256"] = hashlib.sha256(definitions_path.read_bytes()).hexdigest()
    sources["supplied_weather_sha256"] = supplied.sha256
    sources["energyplus"] = {"version": compiler.version,
                            "executable_sha256": compiler.engine_hash, "schema_sha256": compiler.schema_hash}
    args.output.mkdir(parents=True, exist_ok=False)
    # Retain the supplied weather bytes rather than depending on a mutable external path.
    shutil.copyfile(supplied.path, args.output/"supplied.epw")
    supplied = Weather.from_epw(args.output/"supplied.epw", calendar_year=2023)
    synthetic = Weather.from_epw(controlled_weather(args.output/"controlled.epw"), calendar_year=2023)
    sources["controlled_weather_sha256"] = synthetic.sha256
    study = PaperStudy("Core and RC shared fixture comparison",
        "How closely do the engines agree on annual heating, peaks and hourly demand from the same explicit inputs?",
        configuration=definitions, sources=sources)
    cases = []
    for fixture in definitions["cases"]:
        case_id = fixture["case_id"]
        print(f"Running {case_id}", flush=True)
        root = args.output/case_id
        root.mkdir()
        b = Building(preset=definitions["preset"], geometry=GeometrySpec.from_footprint(
            Polygon(fixture["vertices"]), storeys=definitions["storeys"], storey_height_m=definitions["storey_height_m"]))
        b.foundation = FoundationSpec(method="prescribed_temperature")
        b.ground_temperature = GroundTemperatureSpec(
            monthly_temperatures_c=tuple(definitions["ground_temperatures_c"]),
            source="explicit controlled comparison boundary; not a site measurement")
        b.load_reference_area_m2 = fixture["reference_area_m2"]
        b.operation = b.operation.updated(gain_partitions=GainPartitionSpec(
            **definitions["gain_partitions"], people_sensible_heat_fraction=fixture["people_sensible_fraction"]),
            equipment_fraction=ScheduleSpec.constant(definitions["equipment_fraction"]),
            equipment_heat_fraction_schedule=ScheduleSpec(values=tuple(definitions["equipment_heat_fraction_schedule"])),
            lighting_gain_w_m2=definitions["lighting_gain_w_m2"])
        snapshot = b.snapshot()
        (root/"building.json").write_text(json.dumps(snapshot.to_dict(), indent=2)+"\n")
        weather = {"controlled": synthetic, "supplied": supplied}[fixture["weather"]]
        identity = {"building_snapshot_sha256": snapshot.sha256,
                    "physical_inputs_sha256": snapshot.to_spec(weather).physical_hash(),
                    "weather_sha256": weather.sha256}
        results, errors, treatment = {}, {}, {}
        # This study pairs two public engine calls. Prepared scheduling, caching and
        # distributed execution are deliberately left to epsm_workflows.
        for engine in ("energyplus", "rc"):
            try:
                # Each engine receives a fresh reconstruction of the captured snapshot.
                inputs = snapshot.to_building()
                if inputs.to_spec(weather).physical_hash() != identity["physical_inputs_sha256"]:
                    raise ValueError("Reconstructed physical inputs changed")
                result = (run_building(snapshot, weather=weather, energyplus=str(args.energyplus.resolve()),
                            directory=root/engine) if engine == "energyplus" else
                          simulate_building(inputs, weather=weather, directory=root/engine,
                            settings=RCSettings(**definitions["rc_settings"])))
                if inputs.snapshot().sha256 != snapshot.sha256:
                    raise ValueError("Engine modified its captured inputs")
                results[engine] = result
                treatment[engine] = {k: result.diagnostics[k] for k in (
                    "accepted", "gain_reduction", "ground_reduction", "self_shadowing", "approximations")
                    if k in result.diagnostics}
            except Exception as exc:
                errors[engine] = f"{type(exc).__name__}: {exc}"
        case = {"case_id": case_id, "engine_treatment": treatment,
            "assumptions": "Illustrative reference fabric/HVAC/operation; explicit gain channels; shared 18 C monthly ground boundary; RC sensible-only unlimited supply and explicitly omitted self-shadowing. "
                           + ("Synthetic constant weather, not a climate validation." if fixture["weather"] == "controlled"
                              else "Supplied EPW. Concave self-shadowing remains a declared model difference.")}
        if not errors:
            try:
                case["comparison"] = compare_energy_results(results["energyplus"], results["rc"],
                    reference_identity=identity, candidate_identity=identity,
                    expected_time_axis=hourly_axis(2023))
            except Exception as exc:
                errors["comparison"] = f"{type(exc).__name__}: {exc}"
        if errors:
            case["error"] = errors
        cases.append(case)
    paths = write_comparison_report(study, cases, args.output,
        reference_label="EnergyPlus", candidate_label="RC")
    print(paths["html"], flush=True)
    return 0 if all("comparison" in c for c in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
