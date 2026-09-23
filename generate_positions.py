import argparse
import json
import os
import random
import re
import sys
import yaml
from pathlib import Path

import ese

yml_config_file = Path("config/config.yml")
yml_colors_file = Path("config/colors.yml")
combined_ese_input_file = Path("inputs/LFXX.ese")
default_fir_ese_files = [
    Path("inputs/LFBB.ese"),
    Path("inputs/LFEE.ese"),
    Path("inputs/LFFF.ese"),
    Path("inputs/LFMM.ese"),
    Path("inputs/LFRR.ese"),
]
json_output_file = Path("outputs/positions.json")


def get_input_files():
    parser = argparse.ArgumentParser(
        description="Generate positions from one or more ESE files."
    )
    parser.add_argument("ese_files", nargs="*", type=Path)
    args = parser.parse_args()

    if args.ese_files:
        input_files = args.ese_files
    elif all(path.is_file() for path in default_fir_ese_files):
        input_files = default_fir_ese_files
    elif combined_ese_input_file.is_file():
        input_files = [combined_ese_input_file]
    else:
        parser.error(
            "No ESE input found. Add inputs/LFXX.ese, add all five FIR "
            "files, or pass ESE paths on the command line."
        )

    missing = [str(path) for path in input_files if not path.is_file()]
    if missing:
        parser.error("ESE input file(s) not found: " + ", ".join(missing))

    return input_files

# Load Config file
print(f"Loading config file {yml_config_file}")
with open(yml_config_file, "r") as file:
    config = yaml.safe_load(file)

# Load Colors file if it exists
if os.path.exists(yml_colors_file):
    print(f"Loading color file {yml_colors_file}")
    with open(yml_colors_file, "r") as file:
        colors = yaml.safe_load(file)
else:
    print(f"Color file {yml_colors_file} does not exist, will create new one")
    colors = []

# Position IDs are local to each ESE file; resolve every referenced vACC
# callsign to one output ID shared with generate_airspaces/generate_airports.
ese_files = {}
for ese_input_file in get_input_files():
    print(f"Loading ESE file {ese_input_file}")
    ese_files[ese_input_file] = ese.load(ese_input_file)

position_ids = ese.PositionIds(
    ese_files,
    config["config"].get("valid_fir", []),
    config["config"]["valid_callsign"],
)
print(f"Found {len(position_ids.definitions)} positions referenced by sectors")

# Function to get color
def get_position_color(position):
    for color in colors:
        if color["callsign"] == position:
            return color["color"]
    for pattern in config["colors"]:
        if re.search(pattern["callsign"], position):
            # LFXX_CTR: main color, LFXX_X_CTR: randomized color
            if position.count("_") >= 2:
                color = randomize_color(pattern["color"])
            else:
                color = pattern["color"]
            colors.append({"callsign": position, "color": color})
            return color
    return ""

# Function to ramdom color
def randomize_color(color_hex, variance=30):
    r = clamp(int(color_hex[1:3], 16) + random.randint(-variance, variance))
    g = clamp(int(color_hex[3:5], 16) + random.randint(-variance, variance))
    b = clamp(int(color_hex[5:7], 16) + random.randint(-variance, variance))
    return f"#{r:02x}{g:02x}{b:02x}"

def clamp(x):
    return max(0, min(x, 255))

positions = {}
color_errors = False
for id, line_parts in position_ids.definitions.items():
    callsign = line_parts[0]

    if line_parts[6] not in ["ATIS", "GND", "RMP", "DEL"]:
        color = get_position_color(callsign)
        if len(color) > 0:
            position = {
                "callsign" : line_parts[1],
                "frequency" : line_parts[2],
                "type" : line_parts[6],
                "pre" : [line_parts[5]],
                "colours" : [{"hex": color}]
            }
            positions[id] = position 
        else:
            print(f"Error: no colors defined for {id} ({callsign})")
            color_hex = "#ffffff"
            color_errors = True

output = {
    "positions" : positions
}

# Colors errors
if color_errors:
    sys.exit(1)
else:
    print("Was able to find colours for all positions")

# Save updated colors file
print(f"Updating color file {yml_colors_file}")
with open(yml_colors_file, "w") as file:
    yaml.dump(colors, file)

# Store output JSON
print(f"Writing positions to {json_output_file}")
with open(json_output_file, 'w') as outfile:
    json.dump(output, outfile, indent=2)
