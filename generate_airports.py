import json
import re
import requests
import yaml
from pathlib import Path

vatspy_dat_url = "https://raw.githubusercontent.com/vatsimnetwork/vatspy-data-project/refs/heads/master/VATSpy.dat"

ese_input_file = Path("inputs/LFXX.ese")
yml_config_file = Path("config/config.yml")
manual_airports_file = Path("inputs/airports.json")

json_output_file = Path("outputs/airports.json")
missing_output_file = Path("outputs/missing_topdown.txt")


def splitowners(lines):
    owner_lines = [x for x in lines if x.startswith("OWNER:")]
    return owner_lines[0].split(":")[1:] if owner_lines else []


def build_position_airport_map(ese_data, valid_airport, position_regexp):
    position_to_airport = {}
    block = False

    for line in ese_data:
        line = line.strip()

        if line.startswith("[POSITIONS]"):
            block = True
            continue

        if block and line.startswith("["):
            block = False
            continue

        if not block or not line or line.startswith(";"):
            continue

        parts = [p.strip() for p in line.split(":")]

        if len(parts) > 6 and re.search(position_regexp, line):
            sector_code = parts[3]
            airport_icao = parts[5]

            if re.match(valid_airport, airport_icao):
                position_to_airport[sector_code] = airport_icao

    print(f"Found {len(position_to_airport)} position -> airport mappings")
    return position_to_airport


def build_topdown_from_ese(ese_data, valid_airport, position_regexp):
    position_to_airport = build_position_airport_map(
        ese_data,
        valid_airport,
        position_regexp
    )

    sectors = []
    block = False
    sector = ""

    for line in ese_data:
        if line.startswith("SECTOR:"):
            block = True
            sector = line.strip().replace("\u00b7", "·").replace("�", "·")
        elif block and len(line.strip()) == 0:
            block = False
            if "OWNER:" in sector:
                sectors.append(sector)
        elif block and not line.strip().startswith(";"):
            clean_line = line.strip().replace("\u00b7", "·").replace("�", "·")
            sector += "\n" + clean_line

    print(f"Found {len(sectors)} SECTOR blocks with OWNER")

    topdown = {}

    for sector in sectors:
        lines = sector.split("\n")
        owners = splitowners(lines)

        if not owners:
            continue

        for owner in owners:
            if owner in position_to_airport:
                airport_icao = position_to_airport[owner]

                if airport_icao not in topdown:
                    topdown[airport_icao] = owners
                    print(f"ESE TOPDOWN: {airport_icao} -> {owners}")

    print(f"Found {len(topdown)} topdown chains from ESE")
    return topdown


def load_manual_topdown(path):
    if not path.exists():
        print(f"No manual airports file found at {path}")
        return {}

    print(f"Loading manual topdown data from {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    manual = {}

    # New preferred format:
    # [
    #   {"icao": "LFAC", "topdown": ["ACI", "QW", "..."]},
    #   {"icao": "LFAB", "topdown": ["Uncontrolled(?)"]}
    # ]
    if isinstance(data, list):
        for item in data:
            icao = item.get("icao")
            topdown = item.get("topdown")

            if icao and topdown:
                manual[icao] = topdown

    # Backwards-compatible old format:
    # {"airports": {"LFAC": {"topdown": [...]}}}
    elif isinstance(data, dict) and "airports" in data:
        for icao, airport in data.get("airports", {}).items():
            if "topdown" in airport and airport["topdown"]:
                manual[icao] = airport["topdown"]

    print(f"Loaded {len(manual)} manual topdown chains")
    return manual


def write_missing_topdown(path, missing_airports):
    with open(path, "w", encoding="utf-8") as outfile:
        outfile.write("# Airports missing topdown\n")
        outfile.write("# Add these to inputs/airports.json if needed.\n\n")

        for icao, callsign in missing_airports:
            outfile.write(
                json.dumps(
                    {
                        "icao": icao,
                        "callsign": callsign,
                        "topdown": ["Uncontrolled(?)"]
                    },
                    ensure_ascii=False
                )
            )
            outfile.write(",\n")


print(f"Loading config file {yml_config_file}")
with open(yml_config_file, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

valid_airport = config["config"]["valid_airport"]
position_regexp = config["config"]["valid_callsign"]

print(f"Loading {ese_input_file}")
with open(ese_input_file, "r", encoding="cp1252") as file:
    ese_data = file.readlines()

# 1. Build topdown from ESE
topdown_by_airport = build_topdown_from_ese(
    ese_data,
    valid_airport,
    position_regexp
)

# 2. Manual airports.json wins over ESE
manual_topdown = load_manual_topdown(manual_airports_file)

for icao, topdown in manual_topdown.items():
    topdown_by_airport[icao] = topdown
    print(f"MANUAL TOPDOWN: {icao} -> {topdown}")

print(f"Total topdown airport chains: {len(topdown_by_airport)}")

# 3. Load VATSPY data
print(f"Downloading VATSPY data from {vatspy_dat_url}")
response = requests.get(vatspy_dat_url)
response.raise_for_status()
vatspy_data = response.text

airports = {}
missing_topdown = []

for line in vatspy_data.splitlines():
    line_parts = line.split("|")

    if len(line_parts) > 5 and re.match(valid_airport, line_parts[0]):
        icao = line_parts[0]

        airport = {
            "callsign": line_parts[1],
            "coord": [
                float(line_parts[2]),
                float(line_parts[3])
            ]
        }

        if icao in topdown_by_airport:
            airport["default"] = False
            airport["topdown"] = topdown_by_airport[icao]
        else:
            missing_topdown.append((icao, line_parts[1]))

        airports[icao] = airport

print(f"Found {len(airports)} airports")

json_output_file.parent.mkdir(parents=True, exist_ok=True)

output = {
    "airports": airports
}

with open(json_output_file, "w", encoding="utf-8") as outfile:
    json.dump(output, outfile, indent=2, ensure_ascii=False)

write_missing_topdown(missing_output_file, missing_topdown)

print(f"Wrote {json_output_file}")
print(f"Wrote {missing_output_file}")
print(f"Airports without topdown: {len(missing_topdown)}")