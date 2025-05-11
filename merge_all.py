import argparse, json

input_files = [
    "airspace.json",
    "groups.json",
    "positions.json",
    "callsigns.json",
    "airports.json"
]

parser = argparse.ArgumentParser()
parser.add_argument("--input-dir", "-i", dest="input_dir", default="./outputs", help="VATGlass output file")
parser.add_argument("--output-file", "-o", dest="output_file", default="./outputs/lf.json", help="VATGlass output file")
args = parser.parse_args()

final_data = {}

for input_file in input_files:
    file_path = args.input_dir + "/" + input_file
    print(f"Opening {file_path}")
    with open(file_path, "r") as file:
        input_data = json.load(file)
    first_property = list(input_data.keys())[0]
    data_size = (len(list(input_data[first_property])))
    print(f"  Found {data_size} entries")
    final_data = {**final_data, **input_data}

print (f"Writing to {args.output_file}")
with open(args.output_file, "w") as file:
    json.dump(final_data, file, indent=2)

