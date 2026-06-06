import json
import re
import yaml
from pathlib import Path

yml_config_file = Path("config/config.yml")
ese_input_file = Path("inputs/LFXX.ese")
json_output_file = Path("outputs/airspace.json")


def splitowners(line):
    owner_lines = [x for x in line if x.startswith("OWNER:")]
    return owner_lines[0].split(":")[1:] if owner_lines else []


def splitborders(line):
    border_lines = [x for x in line if x.startswith("BORDER:")]
    return border_lines[0].split(":")[1:] if border_lines else []


def splitactive(line):
    active_lines = [x for x in line if x.startswith("ACTIVE:")]
    runways = []

    for active in active_lines:
        parts = active.split(":")
        if len(parts) >= 3:
            icao = parts[1].strip()
            runway = parts[2].strip()

            # 17L / 17R / 17C -> 17
            runway = re.sub(r"[LCR]$", "", runway)

            item = {
                "icao": icao,
                "runway": runway
            }

            if item not in runways:
                runways.append(item)

    return runways


def convert_latitude(coord):
    sign = "-" if coord[0] == "S" else ""
    return sign + coord[2:4] + coord[5:7] + coord[8:10]


def convert_longitude(coord):
    sign = "-" if coord[0] == "W" else ""
    return sign + coord[1:4] + coord[5:7] + coord[8:10]


def getcoor(line):
    coorlines = [x for x in line if x.startswith("COORD:")]
    coors = []

    for coorline in coorlines:
        coorline = coorline.replace("COORD:", "")
        latitude = convert_latitude(coorline.split(":")[0])
        longitude = convert_longitude(coorline.split(":")[1])
        coors.append([latitude, longitude])

    return coors


def chain(dominoes):
    for i in range(len(dominoes) - 1):
        for j in range(i + 1, len(dominoes)):
            if dominoes[i][-1] == dominoes[j][0]:
                dominoes[i] = dominoes[i] + dominoes[j]
            elif dominoes[i][-1] == dominoes[j][-1]:
                dominoes[i] = dominoes[i] + dominoes[j][::-1]
            elif dominoes[i][0] == dominoes[j][0]:
                dominoes[i] = dominoes[j][::-1] + dominoes[i]
            elif dominoes[i][0] == dominoes[j][-1]:
                dominoes[i] = dominoes[j] + dominoes[i]
            else:
                continue

            dominoes.pop(j)

            if len(dominoes) == 1:
                return dominoes[0]

            return chain(dominoes)

    return None


def removesequentialduplicates(coors):
    new_coors = []
    prev = None

    for coor in coors:
        if coor != prev:
            new_coors.append(coor)
        prev = coor

    return new_coors


def getpoints(borders):
    coordinates = []

    for b in borders:
        if b not in linedic:
            print(f"Missing sectorline referenced by border: {b}")
            return None

        coor = linedic[b]["coor"]

        if not coor:
            print(f"Sectorline has no coordinates: {b}")
            return None

        coordinates.append(coor)

    if len(coordinates) == 1:
        return coordinates[0]

    chained = chain(coordinates.copy())

    if chained is None:
        print("\nERROR: Could not chain borders:")
        print(borders)

        for border, fragment in zip(borders, coordinates):
            print(
                f"  {border}: "
                f"{fragment[0] if fragment else 'EMPTY'} -> "
                f"{fragment[-1] if fragment else 'EMPTY'}"
            )

        return None

    return removesequentialduplicates(chained)


def get_group_name(sector):
    fir = sector.split("·")[0]
    sector_name = sector.split("·")[1]

    if sector_name.endswith("_CTR"):
        return "TWR"
    elif fir in config["config"]["valid_fir"]:
        return fir
    else:
        return "OTHER"


print(f"Loading config file {yml_config_file}")
with open(yml_config_file, "r") as file:
    config = yaml.safe_load(file)

fir_list = config["config"]["valid_fir"]
position_regexp = config["config"]["valid_callsign"]

print(f"Loading ESE file {ese_input_file}")
with open(ese_input_file, "r", encoding="cp1252") as file:
    ese_data = file.readlines()

# Extract positions
valid_positions = []
block = False

for line in ese_data:
    if line.startswith("[POSITIONS]"):
        block = True
    elif block and line.startswith("["):
        block = False
    elif block and re.search(position_regexp, line):
        valid_positions.append(line.split(":")[3])

print(f"Found {len(valid_positions)} positions to include/exclude from topdown")

# Extract sectors
sectors = []
block = False

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

print(f"Found {len(sectors)} SECTOR")

# Extract sectorlines
sectorlines = []
block = False

for line in ese_data:
    if line.startswith("SECTORLINE:"):
        block = True
        sectorline = line.strip()
    elif block and len(line.strip()) == 0:
        block = False
        sectorlines.append(sectorline)
    elif block and not line.strip().startswith(";"):
        sectorline += "\n" + line.strip()

print(f"Found {len(sectorlines)} SECTORLINE")

# Build sector dictionary
sectordic = {}

for sector in sectors:
    line = sector.split("\n")
    name = line[0].split(":")[1]
    low = line[0].split(":")[2]
    high = line[0].split(":")[3]
    owners = splitowners(line)
    borders = splitborders(line)
    runways = splitactive(line)

    sectordic[name] = {
        "low": low,
        "high": high,
        "owners": owners,
        "borders": borders,
        "runways": runways,
    }

# Build sectorline dictionary
linedic = {}

for sectorline in sectorlines:
    lines = sectorline.split("\n")
    coor = getcoor(lines)
    name = lines[0].split(":")[1]

    linedic[name] = {
        "coor": coor
    }

# Build output
airspaces = []

for sector in reversed(sectordic.keys()):
    name = sector.split("·")[1]

    if sector.split("·")[0] in fir_list:
        if any(pos in valid_positions for pos in sectordic[sector]["owners"]):
            tmp = {
                "id": name,
                "group": get_group_name(sector),
                "owner": sectordic[sector]["owners"],
            }

            if sectordic[sector]["runways"]:
                tmp["runways"] = sectordic[sector]["runways"]

            tmp["sectors"] = [
                {
                    "min": int(int(sectordic[sector]["low"]) / 100),
                    "max": int(int(sectordic[sector]["high"]) / 100) - 1,
                    "points": getpoints(sectordic[sector]["borders"]),
                }
            ]

            if (
                tmp["sectors"][0]["points"] is not None
                and "_GND" not in name
                and "_RMP" not in name
                and "_DEL" not in name
            ):
                airspaces.append(tmp)
            else:
                print(sector.ljust(30), "is ground, delivery, or invalid")
        else:
            print(sector.ljust(30), "no owner is in this vacc", sectordic[sector]["owners"])
    else:
        print(sector.ljust(30), "not part of this vacc", fir_list)

print(f"Found {len(airspaces)} airspaces")

output = {
    "airspace": airspaces
}

json_output_file.parent.mkdir(parents=True, exist_ok=True)

with open(json_output_file, "w") as outfile:
    json.dump(output, outfile, indent=2)

print(f"Wrote {json_output_file}")