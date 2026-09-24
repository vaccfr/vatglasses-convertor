"""List the airport, position and airspace IDs added or removed between two VATGlasses files.

Informational only: always exits 0.
"""

import argparse
import sys
from collections.abc import Sequence

from vatglasses_convertor import vatglasses


def compare(old_ids: list[str], new_ids: list[str]) -> None:
    print(f"Old: {len(old_ids)}, New: {len(new_ids)}")
    new_set, old_set = set(new_ids), set(old_ids)
    removed = [x for x in old_ids if x not in new_set]
    print(f"In old but not in new: {len(removed)}")
    print(removed)
    added = [x for x in new_ids if x not in old_set]
    print(f"In new but not in old: {len(added)}")
    print(added)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-file", "-o", required=True, help="old VATGlasses file or URL")
    parser.add_argument("--new-file", "-n", required=True, help="new VATGlasses file or URL")
    args = parser.parse_args(argv)

    old_data = vatglasses.load(args.old_file)
    new_data = vatglasses.load(args.new_file)

    print("--- Compare airports ---")
    compare(list(old_data["airports"]), list(new_data["airports"]))
    print("--- Compare positions ---")
    compare(list(old_data["positions"]), list(new_data["positions"]))
    print("--- Compare airspaces ---")
    compare(
        [airspace["id"] for airspace in old_data["airspace"]],
        [airspace["id"] for airspace in new_data["airspace"]],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
