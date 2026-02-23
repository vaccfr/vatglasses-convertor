import json, re, yaml
from pathlib import Path

yml_config_file = Path("config/config.yml")
ese_input_file = Path("inputs/LFXX.ese")
json_output_file = Path("outputs/airspace.json")

# Removes string OWNER from the line and returns all sector owners' names/ids
def splitowners(line):
    line = [x for x in line if x.startswith("OWNER:")]
    try:
        return line[0].split(":")[1:]
    except:
        # If this also fails: enable print and search for the owner name in the ese. Check if the line/list above/under is not empty/exists. This might be because the current line does not have a OWNER attirbute in the ESE.  - Check the ese!
        return line[0]

# Removes string BORDER from the line and returns all borderlines' names/numbers
def splitborders(line):
    line = [x for x in line if x.startswith("BORDER:")]
    try:
        return line[0].split(":")[1:]
    except:
        # If this also fails: enable print and search for the border name in the ese. Check if the line/list above/under is not empty/exists. This might be because the current line does not have a BORDER attirbute in the ESE.  - Check the ese!
        return line[0]

# Convert coordinate to right format
# N041.47.26.600 > 414726600
def convert_latitude(coord):
    sign = "-" if coord[0] == "S" else ""
    converted_coord = sign + coord[2:4] + coord[5:7] + coord[8:10]
    return converted_coord

# E010.32.35.197 > 0103235197
def convert_longitude(coord):
    sign = "-" if coord[0] == "W" else ""
    converted_coord = sign + coord[1:4] + coord[5:7] + coord[8:10]
    return converted_coord

# Formats all coordinates of a given sectorline
def getcoor(line):
    coorlines = [x for x in line if x.startswith("COORD:")]
    coors = []
    for coorline in coorlines:
        coorline = coorline.replace("COORD:", "")
        latitude = convert_latitude(coorline.split(":")[0])
        longitude = convert_longitude(coorline.split(":")[1])
        coorline = [latitude,longitude]
        coors.append(coorline)
    return coors

# Connects all sector lines into one big line
def chain(dominoes):
    #print("\n",dominoes)
    #print("Before", linedic["176"])
    for i in range(len(dominoes) - 1):
        for j in range(len(dominoes) - 1):
            j += i + 1

            if dominoes[i][-1] == dominoes[j][0]: # head == tail
                #print("head=tail",dominoes[i],dominoes[j])
                rev = dominoes[j]
                new_list = dominoes[i] + rev
                dominoes[i] = new_list
                #dominoes[i].extend(rev)
                dominoes.remove(dominoes[j])
            
                if len(dominoes) == 1:
                    return dominoes[0]
                else:
                    return chain(dominoes)

            elif dominoes[i][-1] == dominoes[j][-1]: # head == head
                #print("head=head",dominoes[i][-1],dominoes[i],dominoes[j])
                rev = dominoes[j][::-1]
                new_list = dominoes[i] + rev
                dominoes[i] = new_list
                #dominoes[i].extend(rev)
                dominoes.remove(dominoes[j])
                
                if len(dominoes) == 1:
                    return dominoes[0]
                else:
                    return chain(dominoes)

            elif dominoes[i][0] == dominoes[j][0]: # tail == tail
                #print("tail=tail",dominoes[i][0],dominoes[i],dominoes[j])
                dominoes[i] = dominoes[j][::-1] + dominoes[i]
                dominoes.remove(dominoes[j])
                
                if len(dominoes) == 1:
                    return dominoes[0]
                else:
                    return chain(dominoes)

            elif dominoes[i][0] == dominoes[j][-1]: # tail == head
                #print("tail=head",dominoes[i][0],dominoes[i],dominoes[j])
                dominoes[i] = dominoes[j] + dominoes[i]
                dominoes.remove(dominoes[j])
                
                if len(dominoes) == 1:
                    return dominoes[0]
                else:
                    return chain(dominoes)

def removesequentialduplicates(coors):
    new_coors = []
    prev = ""
    
    for coor in coors:
        if coor != prev:
            new_coors.append(coor)
        prev = coor
    
    return new_coors

#Creates a nested list of the secotors' coordinates
def getpoints(borders):
    coordinates = []
    for b in borders:
        coordinates.append(linedic[b]["coor"])

    if len(coordinates) == 1:
        return coordinates[0]
    else:    
        coordinates_copy = coordinates.copy()
        return removesequentialduplicates(chain(coordinates_copy))

# Used to assign the sector a group based on the sectors' name
def get_group_name(sector):

    fir = sector.split("·")[0]
    sector_name = sector.split("·")[1]

    if sector_name.endswith("_CTR"):
        return "TWR"
    elif fir in config["config"]["valid_fir"]:
        return fir
    else:
        return "OTHER"

# Load Config file
print(f"Loading color file {yml_config_file}")
with open(yml_config_file, "r") as file:
    config = yaml.safe_load(file)
fir_list = config["config"]["valid_fir"]
position_regexp = config["config"]["valid_callsign"]

# Load ESE file
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
print(f"Found {len(valid_positions)} TWR positions to exclude from topdown")

# Extract sectors
sectors = []
block = False
for line in ese_data:
    if line.startswith("SECTOR:"):
        block = True
        sector = line.strip()
    elif block and len(line.strip()) == 0:
        block = False
        if "OWNER:" in sector:
            sectors.append(sector)
    elif block and not line.strip().startswith(";"):
            line = line.replace("\u00b7","·").replace("�","·")
            sector += "\n" + line.strip()
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
    
# Build dictionary with information about the sectors (no coordinates yet, only border names/numbers)
sectordic = {}
for sector in sectors:
    line = sector.split("\n")
    name = line[0].split(":")[1]
    low = line[0].split(":")[2]
    high = line[0].split(":")[3]
    owners = splitowners(line)
    borders = splitborders(line)
    
    sectordic[name] = {
        "low": low,
        "high" : high,
        "owners" : owners,
        "borders": borders,
    }

# Dictionary of linedic<sectorline_name> = {coor : [[bla,blabla][bla,bla,bla]]}
linedic = {}
for sectorline in sectorlines:
    if sectorline.startswith("\n"):
        sectorline = sectorline[2:]

    lines = sectorline.split("\n")
    coor = getcoor(lines)
    
    name = lines[0].split(":")[1]

    linedic[name] = {
        "coor" : coor
    }

# Creates the output and is the heart of the code
airspaces = []
for sector in reversed(sectordic.keys()):
    name = sector.split("·")[1]
    
    if sector.split("·")[0] in fir_list: #If this sector is a sector of the vacc
        if any(pos in valid_positions for pos in sectordic[sector]["owners"]):
            tmp = {}
            tmp["id"] = name
            tmp["group"] = get_group_name(sector)
            tmp["owner"] = sectordic[sector]["owners"]
            tmp["sectors"] = [ {
                "min" : int(int(sectordic[sector]["low"])/100) ,
                "max": int(int(sectordic[sector]["high"])/100) -1,
                "points" : getpoints(sectordic[sector]["borders"])
            }]

            if tmp["sectors"][0]["points"] != None and "_GND" not in name and "_RMP" not in name and "_DEL" not in name: #and "-GND" not in name
                airspaces.append(tmp)
            else:
                print(sector.ljust(30), "         is ground or delivery")
        else:
            print(sector.ljust(30), "         no owner are in this vacc", sectordic[sector]["owners"])
    else:
        print(sector.ljust(30),"         not part of this vacc", fir_list)
print(f"Found {len(airspaces)} airspaces")

output = {
    "airspace":  airspaces
}

# Directly from dictionary
with open(json_output_file, 'w') as outfile:
    json.dump(output, outfile, indent=2)
