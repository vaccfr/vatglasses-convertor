import argparse
import json
import re
import yaml
from pathlib import Path

yml_config_file = Path("config/config.yml")
combined_ese_input_file = Path("inputs/LFXX.ese")
default_fir_ese_files = [
    Path("inputs/LFBB.ese"),
    Path("inputs/LFEE.ese"),
    Path("inputs/LFFF.ese"),
    Path("inputs/LFMM.ese"),
    Path("inputs/LFRR.ese"),
]
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


def getpoints(borders, linedic):
    coordinates = []

    for b in borders:
        if b not in linedic:
            print(f"Missing sectorline referenced by border: {b}")
            return None

        coor = linedic[b]["coor"]

        if not coor:
            print(f"Sectorline has no coordinates: {b}")
            return None

        # Ignore zero-length helper lines such as ORLY sectorline 166,
        # whose coordinates are the same point repeated twice.
        if len({tuple(point) for point in coor}) < 2:
            continue

        coordinates.append(coor)

    if not coordinates:
        return None

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


def get_input_files():
    parser = argparse.ArgumentParser(
        description="Generate vatglasses airspaces from one or more ESE files."
    )
    parser.add_argument(
        "ese_files",
        nargs="*",
        type=Path,
        help="ESE files to merge (for example inputs/LFBB.ese ... inputs/LFRR.ese)",
    )
    args = parser.parse_args()

    if args.ese_files:
        input_files = args.ese_files
    elif all(path.is_file() for path in default_fir_ese_files):
        input_files = default_fir_ese_files
    elif combined_ese_input_file.is_file():
        input_files = [combined_ese_input_file]
    else:
        expected = ", ".join(str(path) for path in default_fir_ese_files)
        parser.error(
            f"No ESE input found. Add {combined_ese_input_file}, add all of "
            f"{expected}, or pass ESE paths on the command line."
        )

    missing = [str(path) for path in input_files if not path.is_file()]
    if missing:
        parser.error("ESE input file(s) not found: " + ", ".join(missing))

    return input_files


def extract_positions(ese_data):
    positions = []
    block = False

    for line in ese_data:
        if line.startswith("[POSITIONS]"):
            block = True
        elif block and line.startswith("["):
            block = False
        elif block and re.search(position_regexp, line):
            parts = line.split(":")
            if len(parts) > 3:
                positions.append(parts[3].strip())

    return positions


def extract_sectors(ese_data):
    sectors = []
    sector = None

    for line in ese_data:
        if line.startswith("SECTOR:"):
            if sector is not None and "OWNER:" in sector:
                sectors.append(sector)
            sector = line.strip()
        elif sector is not None and not line.strip():
            if "OWNER:" in sector:
                sectors.append(sector)
            sector = None
        elif sector is not None and not line.strip().startswith(";"):
            sector += "\n" + line.strip()

    if sector is not None and "OWNER:" in sector:
        sectors.append(sector)

    return sectors


def extract_sectorlines(ese_data):
    sectorlines = []
    sectorline = None

    for line in ese_data:
        if line.startswith("SECTORLINE:"):
            if sectorline is not None:
                sectorlines.append(sectorline)
            sectorline = line.strip()
        elif sectorline is not None and not line.strip():
            sectorlines.append(sectorline)
            sectorline = None
        elif sectorline is not None and not line.strip().startswith(";"):
            sectorline += "\n" + line.strip()

    if sectorline is not None:
        sectorlines.append(sectorline)

    return sectorlines


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
ese_input_files = get_input_files()
valid_positions = set()
datasets = []

for ese_input_file in ese_input_files:
    print(f"Loading ESE file {ese_input_file}")
    with open(ese_input_file, "r", encoding="utf-8-sig") as file:
        ese_data = file.readlines()

    # FIR-specific files can still contain neighbouring or shared sectors.
    # Only retain sectors whose FIR prefix matches the input filename.
    source_fir = ese_input_file.stem.upper()
    if source_fir not in fir_list:
        source_fir = None

    file_positions = extract_positions(ese_data)
    sectors = extract_sectors(ese_data)
    if source_fir is not None:
        sectors = [
            sector
            for sector in sectors
            if sector.split("\n", 1)[0].split(":", 2)[1].split("·", 1)[0]
            == source_fir
        ]
    sectorlines = extract_sectorlines(ese_data)
    valid_positions.update(file_positions)

    print(
        f"  Found {len(file_positions)} positions, "
        f"{len(sectors)} sectors"
        f"{' for ' + source_fir if source_fir else ''}, "
        f"and {len(sectorlines)} sectorlines"
    )

    # Keep a separate dictionary for every ESE file. Numeric sectorline IDs
    # are local to an ESE and may be reused by another FIR's file.
    linedic = {}
    for sectorline in sectorlines:
        lines = sectorline.split("\n")
        coor = getcoor(lines)
        # Declarations can contain an inline comment, for example:
        # "SECTORLINE:1894 ; GLO18288-GLO36927".
        name = lines[0].split(":", 1)[1].split(";", 1)[0].strip()
        linedic[name] = {"coor": coor}

    sectordic = {}
    for sector in sectors:
        lines = sector.split("\n")
        header = lines[0].split(":")
        name = header[1]
        sectordic[name] = {
            "low": header[2],
            "high": header[3],
            "owners": splitowners(lines),
            "borders": splitborders(lines),
            "runways": splitactive(lines),
        }

    datasets.append((ese_input_file, sectordic, linedic))

print(f"Found {len(valid_positions)} unique positions across all input files")

# Build output
airspaces = []

for ese_input_file, sectordic, linedic in reversed(datasets):
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
                        "points": getpoints(
                            sectordic[sector]["borders"], linedic
                        ),
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
                print(
                    sector.ljust(30),
                    "no owner is in this vacc",
                    sectordic[sector]["owners"],
                )
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
