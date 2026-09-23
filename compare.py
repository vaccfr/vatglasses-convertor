import argparse
from vatglasses import load

parser = argparse.ArgumentParser()
parser.add_argument("--old-file", "-o", dest="old_file", required=True, help="Old file")
parser.add_argument("--new-file", "-n", dest="new_file", required=True, help="new file")
args = parser.parse_args()

old_data = load(args.old_file)
new_data = load(args.new_file)

def compare(old_list, new_list):
    print(f"Old: {len(old_list)}, New: {len(new_list)}")
    diff = [x for x in old_list if x not in new_list]
    print(f"In old but not in new: {len(diff)}")    
    print(diff)
    diff = [x for x in new_list if x not in old_list]
    print(f"In new but not in old: {len(diff)}")
    print(diff)


print(f"--- Compare airports ---")
compare(
    [x for x in old_data["airports"]], 
    [x for x in new_data["airports"]]
)

print(f"--- Compare positions ---")
compare(
    [x for x in old_data["positions"]], 
    [x for x in new_data["positions"]]
)

print(f"--- Compare airspaces ---")
compare(
    [x["id"] for x in old_data["airspace"]], 
    [x["id"] for x in new_data["airspace"]]
)
