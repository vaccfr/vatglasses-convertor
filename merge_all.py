"""Merge the per-section JSON files into the final VATGlasses file (outputs/lf.json)."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from vatglasses_convertor import vatglasses
from vatglasses_convertor.config import OUTPUTS_DIR

# Each file holds one top-level section; on key collisions the later file wins.
SECTION_FILES = (
    "airspace.json",
    "groups.json",
    "positions.json",
    "callsigns.json",
    "airports.json",
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", "-i", type=Path, default=OUTPUTS_DIR,
        help="directory holding the section files (default: %(default)s)",
    )
    parser.add_argument(
        "--output-file", "-o", type=Path, default=OUTPUTS_DIR / "lf.json",
        help="merged VATGlasses output file (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    merged = {}
    for name in SECTION_FILES:
        path = args.input_dir / name
        print(f"Opening {path}")
        section = vatglasses.load(path)
        for key, entries in section.items():
            print(f"  Found {len(entries)} entries in {key}")
        merged.update(section)

    vatglasses.save(args.output_file, merged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
