import yaml, json, re, sys
from pathlib import Path

yml_config_file = Path("config/config.yml")
ese_input_file = Path("inputs/LFXX.ese")
json_output_file = Path("outputs/positions.json")

# Attempt to create random colors for every position, but in a way that also attempts to keep similar tints for similar positions types
def similarhex(position):
    import random
    if position == "APP" or position == "DEP":
        color = (0,0,random.randint(0, 255)) #"blue"
    
    elif position == "CTR":
        color = (random.randint(0, 255),140,0) #"orange"

    else:
        color = (0,random.randint(0, 255),0) #green

    r, g, b = color

    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

# File like

# ; ACC ------------------------------------
# Brussels West/Combined Control:Brussels Control:131.100:BW:W:EBBU:CTR:-:-:7101:7177
# Brussels East Control:Brussels Control:129.575:BE:E:EBBU:CTR:-:-:7101:7177

# Brussels NLS Control:Brussels Control:128.800:BN:N:EBBU:CTR:-:-:7101:7177
# Brussels HUS Control:Brussels Control:128.200:BH:H:EBBU:CTR:-:-:7101:7177
# Br
# ussels LUS Control:Brussels Control:125.000:BL:L:EBBU:CTR:-:-:7101:7177
# Brussels WHS Control:Brussels Control:127.225:BC:C:EBBU:CTR:-:-:7101:7177

# Brussels Supervisor:Brussels Supervisor:199.998:BSUP:S:EBBU:CTR:-:-:7101:7177
# Brussels Information:Brussels Information:126.900:BI:I:EBBU:CTR:-:-:0040:0047

# ; UAC ------------------------------------
# Brussels Upper Control:Maastricht Radar:126.000:BU:U:EBBU:CTR:-:-:7101:7177

# Maastricht NIK:Maastricht Radar:135.975:YN:N:EDYY:CTR:-:-:7101:7177
# Maastricht LNO:Maastricht Radar:132.850:YO:O:EDYY:CTR:-:-:7101:7177
# Maastricht KOK:Maastricht Radar:132.200:YK:K:EDYY:CTR:-:-:7101:7177
# Maastricht LUX:Maastricht Radar:133.350:YL:L:EDYY:CTR:-:-:7101:7177

# ;Maastricht NIK HIGH:Maastricht Radar:132.750:YNH:A:EDYY:CTR:-:-:7101:7177
# ;Maastricht LUX HIGH:Maastricht Radar:132.350:YLH:Z:EDYY:CTR:-:-:7101:7177

# Load Config file
print(f"Loading color file {yml_config_file}")
with open(yml_config_file, "r") as file:
    config = yaml.safe_load(file)

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
    for pattern in config["colors"]:
        if re.search(pattern["callsign"], position):
            return pattern["color"]
    return ""

positions = {}
colour_errors = False
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
            colour_hex = "#ffffff"
            colour_errors = True

output = {
    "positions" : positions
}

# Colousr errors
if colour_errors:
    sys.exit(1)
else:
    print("Was able to find colours for all positions")

# Directly from dictionary
with open(json_output_file, 'w') as outfile:
    json.dump(output, outfile, indent=2)