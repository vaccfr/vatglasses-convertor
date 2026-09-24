"""Export the airspaces active at one flight level as GeoJSON, e.g. for geojson.io.

Each airspace is coloured after its owner: the first position of its owner list that is
open (``--positions``, default all positions).
"""

import argparse
import json
import re
import sys
from collections.abc import Sequence

from geojson import Feature, FeatureCollection, Polygon, dumps

from vatglasses_convertor import vatglasses

DEFAULT_COLOR = "#ffffff"


def load_documents(sources: Sequence[str]) -> tuple[list[dict], dict[str, dict]]:
    """Concatenated airspaces and merged positions (later files win) of VATGlasses files."""
    airspaces: list[dict] = []
    positions: dict[str, dict] = {}
    for source in sources:
        document = vatglasses.load(source)
        airspaces.extend(document["airspace"])
        positions.update(document["positions"])
    return airspaces, positions


def position_color(position: dict) -> str:
    colours = position.get("colours") or [{"hex": DEFAULT_COLOR}]
    return colours[0]["hex"]


def build_features(
    airspaces: Sequence[dict],
    positions: dict[str, dict],
    opened: Sequence[str],
    flight_level: int,
    sector_regexp: str | None,
) -> list[Feature]:
    features = []
    for airspace in airspaces:
        if sector_regexp is not None and not re.search(sector_regexp, airspace["id"]):
            continue
        owner = next((owner for owner in airspace["owner"] if owner in opened), None)
        if owner is None:
            continue
        color = position_color(positions.get(owner, {}))

        for sector in airspace["sectors"]:
            sector_min, sector_max = vatglasses.sector_levels(sector)
            if not sector_min <= flight_level <= sector_max:
                continue
            print(
                f"{airspace['id'].ljust(25)} {str(sector_min).ljust(3)}:"
                f"{str(sector_max).ljust(3)} {owner.ljust(4)} {color}"
            )
            polygon = Polygon([vatglasses.ring(sector["points"], airspace["id"])])
            properties = {
                "name": airspace["id"],
                "owner": owner,
                "owners": airspace["owner"],
                "min": sector_min,
                "cur": flight_level,
                "max": sector_max,
                "color_hex": color,
                "stroke": color,
                "stroke-width": 1,
                "stroke-opacity": 0.7,
                "fill": color,
                "fill-opacity": 0.3,
            }
            features.append(Feature(geometry=polygon, properties=properties))
    return features


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-files", "-i", nargs="*", required=True,
                        help="VATGlasses input files or URLs")
    parser.add_argument("--output-file", "-o", help="GeoJSON output file")
    parser.add_argument("--show", "-s", action="store_true", help="show on geojson.io")
    parser.add_argument("--flight-level", "-f", dest="flight_level", required=True,
                        type=int, help="flight level")
    parser.add_argument("--positions", "-p", nargs="*",
                        help="space separated list of open position IDs (default: all)")
    parser.add_argument("--sector-regexp", help="regular expression filtering airspace IDs")
    args = parser.parse_args(argv)

    airspaces, positions = load_documents(args.input_files)
    opened = args.positions or list(positions)
    print(f"Open positions: {opened}")

    try:
        features = build_features(
            airspaces, positions, opened, args.flight_level, args.sector_regexp
        )
    except ValueError as exc:
        print(f"export_geojson: error: {exc}", file=sys.stderr)
        return 1

    if not features:
        print("No matching airspace found for the given flight level and positions.")
        return 0
    print(f"Total matching airspaces: {len(features)}")
    collection = FeatureCollection(features)

    if args.output_file:
        print(f"Write to file {args.output_file}")
        with open(args.output_file, "w", encoding="utf-8") as outfile:
            json.dump(collection, outfile, indent=2)

    if args.show:
        import geojsonio  # only needed to open geojson.io

        geojsonio.display(dumps(collection))
    return 0


if __name__ == "__main__":
    sys.exit(main())
