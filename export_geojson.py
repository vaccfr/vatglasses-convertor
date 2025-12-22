import argparse, geojsonio, json, re
from geojson import Feature, FeatureCollection, Polygon, dump, dumps

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--input-files", "-i", dest="input_files", nargs="*", required=True, help="VATGlass input file")
parser.add_argument("--output-file", "-o", dest="output_file", required=False, help="GeoJSON output file")
parser.add_argument("--show", "-s", dest="show", required=False, action="store_true", help="Show on geojson.io")
parser.add_argument("--flight-level", "-f", dest="flightlevel", required=True, type=int, help="Flight Level")
parser.add_argument("--positions", "-p", nargs="*", help="Space separated list of position codes")
parser.add_argument("--sector-regexp", dest="sector_regexp", help="Regular Express to filter sector")
args = parser.parse_args()

# Open VATGlass input file
data = {
    "airspace": [], 
    "positions": {}
}
for input_file in args.input_files:
    with open(input_file, "r") as file:
        d =  json.load(file)
        for airspace in d["airspace"]:
            data["airspace"].append(airspace)
        for position in d["positions"]:
            print(f" Position {position}")
            data["positions"][position] = d["positions"][position]

# Determine opened positions
if (args.positions):
    opened_positions = args.positions
else:
    opened_positions = list(data["positions"].keys())
print(opened_positions)

# Convert 'N' and 'W' formatted points to decimal degrees
def latitude_to_decimal(dms):  
    sign = -1 if dms[0] == '-' else 1
    dms = dms.lstrip('+-')
    degrees = int(dms[:2])  # First 3 digits
    minutes = int(dms[2:4]) # Next 2 digits
    seconds = int(dms[4:]) if len(dms) > 5 else 0  # Remaining digits (optional)
    decimal_degrees = sign * (degrees + minutes / 60 + seconds / 3600)
    return decimal_degrees

def longitude_to_decimal(dms):  
    sign = -1 if dms[0] == '-' else 1
    dms = dms.lstrip('+-')
    degrees = int(dms[:3])  # First 3 digits
    minutes = int(dms[3:5]) # Next 2 digits
    seconds = int(dms[5:]) if len(dms) > 5 else 0  # Remaining digits (optional)
    decimal_degrees = sign * (degrees + minutes / 60 + seconds / 3600)
    return decimal_degrees

def convert_coordinates(point):
    latitude, longitude = point
    lat_dec = latitude_to_decimal(latitude)
    lon_dec = longitude_to_decimal(longitude)
    return (lon_dec, lat_dec)

# Get Position HEX color
def get_position_color(position):
    if "colours" in data["positions"][position]:
        for color in data["positions"][position]["colours"]:
            return color["hex"]
    else:
        return "#ffffff"

feature_list = []
for airspace in data["airspace"]:
    
    if args.sector_regexp is None or re.search(args.sector_regexp, airspace["id"]):

        matching_owner = None
        for owner in airspace["owner"]:
            if owner in opened_positions:
                matching_owner = owner
                matching_color = get_position_color(matching_owner)
                break

        if matching_owner:
            for sector in airspace["sectors"]:
                sector_min = sector["min"] if "min" in sector else 0
                sector_max = sector["max"] if "max" in sector else 660
                if args.flightlevel >= sector_min and args.flightlevel <= sector_max:
                    print(f"{airspace['id'].ljust(25)} {str(sector_min).ljust(3)}:{str(sector_max).ljust(3)} {matching_owner.ljust(4)} {matching_color}")
                    converted_points = [convert_coordinates(point) for point in sector["points"]]
                    polygon = Polygon([converted_points])
                    properties = {
                        "name": airspace["id"],
                        "owner": matching_owner,
                        "owners": airspace["owner"],
                        "min": sector_min,
                        "cur": args.flightlevel,
                        "max": sector_max,
                        "color_hex": matching_color,
                        "stroke": matching_color,
                        "stroke-width": 1,
                        "stroke-opacity": 0.7,
                        "fill": matching_color,
                        "fill-opacity": 0.3
                    }
                    feature = Feature(geometry=polygon, properties=properties)
                    feature_list.append(feature)
feature_collection = FeatureCollection(feature_list)

if (len(feature_list) == 0):
    print("No matching airspace found for the given flight level and positions.")
else:
    print(f"Total matching airspaces: {len(feature_list)}")
    feature_collection = FeatureCollection(feature_list)

    if args.output_file:
        print(f"Write to file {args.output_file}")
        with open(args.output_file, 'w') as outfile:
            json.dump(feature_collection, outfile, indent=2)

    # Write output file
    if args.show:
        geojsonio.display(dumps(feature_collection))





