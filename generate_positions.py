import yaml, json, random, re, os, sys
from pathlib import Path

yml_config_file = Path("config/config.yml")
yml_colors_file = Path("config/colors.yml")
ese_input_file = Path("inputs/LFXX.ese")
json_output_file = Path("outputs/positions.json")

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

# Load ESE data
print(f"Loading ESE file {ese_input_file}")
with open(ese_input_file, "r", encoding="cp1252") as file:
    ese_data = file.readlines()

# Extract positions
ese_positions = []
block = False
for line in ese_data:
    if line.startswith("[POSITIONS]"):
        block = True
    elif block and line.startswith("["):
        block = False
    elif block and re.search(config["config"]["valid_callsign"], line):
        ese_positions.append(line)

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
for pos in ese_positions:
    line_parts = pos.split(":")
    callsign = line_parts[0]
    id = line_parts[3]

    if line_parts[6] not in ["ATIS", "GND", "DEL"]:
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