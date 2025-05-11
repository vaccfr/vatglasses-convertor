import json, re, requests, yaml
from pathlib import Path

vatspy_dat_url = "https://raw.githubusercontent.com/vatsimnetwork/vatspy-data-project/refs/heads/master/VATSpy.dat"
ese_input_file = Path("inputs/LFXX.ese")
yml_config_file = Path("config/config.yml")
json_output_file = Path("outputs/airports.json")

# Load Config file
print(f"Loading color file {yml_config_file}")
with open(yml_config_file, "r") as file:
    config = yaml.safe_load(file)
valid_airport = config["config"]["valid_airport"]

# Load ESE file
print(f"Loading {ese_input_file}")
with open(ese_input_file, "r", encoding="cp1252") as file:
    ese_data = file.readlines()

# Extract positions
tower_positions = []
block = False
for line in ese_data:
    if line.startswith("[POSITIONS]"):
        block = True
    elif block and line.startswith("["):
        block = False
    elif block and re.match(valid_airport, line) and "_TWR" in line:
        tower_positions.append(line.split(":")[3])
print(f"Found {len(tower_positions)} TWR positions")

# Extract the airport CTR with their ownership
block = False
ctr_owners = {}
for line in ese_data:
    match = re.search(f"SECTOR:.*({ valid_airport })[_-]CTR", line)
    if match:
        airport = match[1]
        block = True
    if block and line.startswith("OWNER:"):
        owners = line.strip().split(":")[1:]
        block = False
        ctr_owners[airport] = owners
print(f"Found {len(ctr_owners)} CTR sectors in ESE")

# Load VATSPY data
print(f"Download VATSPY data from {vatspy_dat_url}")
response = requests.get(vatspy_dat_url)
vatspy_data = response.text

# Build airports dictionnary
airports = {}
for line in vatspy_data.split("\n"):
    line_parts = line.split("|")
    # Filter airports in France Metropolitan and line describes an airport
    if re.match(valid_airport, line_parts[0]) and len(line_parts) > 5: 
        airport = {}
        airport["callsign"] = line_parts[1]
        airport["coord"] =  [float(line_parts[2]),float(line_parts[3])]
        if line_parts[0] in ctr_owners:
            airport["topdown"] = [x for x in ctr_owners[line_parts[0]] if x not in tower_positions]
        airports[line_parts[0]] = airport
print(f"Found {len(airports.keys())} airports")

# Build final dictionnary
output = {
    "airports" : airports
}

# Write output file
with open(json_output_file, 'w') as outfile:
    json.dump(output, outfile, indent=2)

