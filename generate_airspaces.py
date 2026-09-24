"""Generate outputs/airspace.json, the VATGlasses "airspace" section, from ESE files."""

import re
import sys
from collections.abc import Sequence
from itertools import combinations

from vatglasses_convertor import ese, vatglasses
from vatglasses_convertor.config import OUTPUTS_DIR, load_config

OUTPUT_FILE = OUTPUTS_DIR / "airspace.json"
GROUND_MARKERS = ("_GND", "_RMP", "_DEL")

Coordinate = list[str]  # VATGlasses [lat, lon], e.g. ["432809", "-0013115"]


def convert_latitude(coord: str) -> str:
    """N043.28.09.282 -> 432809 (truncated to whole seconds)."""
    sign = "-" if coord[0] == "S" else ""
    return sign + coord[2:4] + coord[5:7] + coord[8:10]


def convert_longitude(coord: str) -> str:
    """W001.31.15.944 -> -0013115 (truncated to whole seconds)."""
    sign = "-" if coord[0] == "W" else ""
    return sign + coord[1:4] + coord[5:7] + coord[8:10]


def convert_points(points: Sequence[ese.Point]) -> list[Coordinate]:
    return [[convert_latitude(lat), convert_longitude(lon)] for lat, lon in points]


def join(first: list[Coordinate], second: list[Coordinate]) -> list[Coordinate] | None:
    """Join two polylines sharing an end point, reversing ``second`` if needed."""
    if first[-1] == second[0]:
        return first + second
    if first[-1] == second[-1]:
        return first + second[::-1]
    if first[0] == second[0]:
        return second[::-1] + first
    if first[0] == second[-1]:
        return second + first
    return None


def chain(fragments: list[list[Coordinate]]) -> list[Coordinate] | None:
    """Chain polylines into one line, or None if some fragment cannot be attached.

    Repeatedly joins the first joinable pair (in index order) until one line remains.
    """
    fragments = list(fragments)
    while len(fragments) > 1:
        for i, j in combinations(range(len(fragments)), 2):
            joined = join(fragments[i], fragments[j])
            if joined is not None:
                fragments[i] = joined
                del fragments[j]
                break
        else:
            return None
    return fragments[0]


def remove_sequential_duplicates(points: list[Coordinate]) -> list[Coordinate]:
    return [point for i, point in enumerate(points) if i == 0 or point != points[i - 1]]


def sector_points(
    borders: Sequence[str], sectorlines: dict[str, tuple[ese.Point, ...]]
) -> list[Coordinate] | None:
    """Chain the border sectorlines of a sector into one ring; None (reported) on error."""
    fragments: list[tuple[str, list[Coordinate]]] = []  # (border ID, points)
    for border in borders:
        if border not in sectorlines:
            print(f"Missing sectorline referenced by border: {border}")
            return None

        points = convert_points(sectorlines[border])
        if not points:
            print(f"Sectorline has no coordinates: {border}")
            return None

        # Ignore zero-length helper lines such as ORLY sectorline 166,
        # whose coordinates are the same point repeated twice.
        if len({tuple(point) for point in points}) < 2:
            continue

        fragments.append((border, points))

    if not fragments:
        return None
    if len(fragments) == 1:
        return fragments[0][1]

    chained = chain([points for _, points in fragments])
    if chained is None:
        print("\nERROR: Could not chain borders:")
        print(list(borders))
        for border, fragment in fragments:
            print(f"  {border}: {fragment[0]} -> {fragment[-1]}")
        return None

    return remove_sequential_duplicates(chained)


def runways(active: Sequence[tuple[str, str]]) -> list[dict[str, str]]:
    """Unique active runways, without L/C/R suffix (17L -> 17)."""
    result = []
    for icao, runway in active:
        item = {"icao": icao, "runway": re.sub(r"[LCR]$", "", runway)}
        if item not in result:
            result.append(item)
    return result


def group_name(sector: ese.Sector, valid_fir: Sequence[str]) -> str:
    if sector.local_name.endswith("_CTR"):
        return "TWR"
    if sector.fir in valid_fir:
        return sector.fir
    return "OTHER"


def build_airspace(
    sector: ese.Sector,
    sectorlines: dict[str, tuple[ese.Point, ...]],
    valid_fir: Sequence[str],
) -> dict | None:
    """VATGlasses airspace entry for ``sector``, or None if it has no usable border."""
    airspace = {
        "id": sector.local_name,
        "group": group_name(sector, valid_fir),
        "owner": list(sector.owners),
    }
    if sector.active:
        airspace["runways"] = runways(sector.active)

    points = sector_points(sector.borders, sectorlines)
    if points is None:
        return None
    airspace["sectors"] = [
        {
            # Stacked bands must not overlap: 66000 ft -> max FL659.
            "min": sector.low_ft // 100,
            "max": sector.high_ft // 100 - 1,
            "points": points,
        }
    ]
    return airspace


def main(argv: Sequence[str] | None = None) -> int:
    config = load_config()
    input_files = ese.parse_input_files(
        "Generate VATGlasses airspaces from one or more ESE files.", argv
    )
    callsign_re = re.compile(config.valid_callsign)

    ese_files = []
    vacc_positions = set()
    for path in input_files:
        ese_file = ese.load(path, config.valid_fir)
        file_positions = [
            position.id
            for position in ese_file.positions
            if callsign_re.search(position.callsign)
        ]
        vacc_positions.update(file_positions)
        ese_files.append(ese_file)

        fir_note = f" for {ese_file.source_fir}" if ese_file.source_fir else ""
        print(
            f"  Found {len(file_positions)} positions, "
            f"{len(ese_file.sectors)} sectors{fir_note}, "
            f"and {len(ese_file.sectorlines)} sectorlines"
        )

    print(f"Found {len(vacc_positions)} unique positions across all input files")

    airspaces = []
    for ese_file in reversed(ese_files):
        # A redefined sector keeps its first position but takes the last definition.
        sectors = {sector.name: sector for sector in ese_file.sectors}
        for sector in reversed(sectors.values()):
            label = sector.name.ljust(30)
            if sector.fir not in config.valid_fir:
                print(label, "not part of this vacc", list(config.valid_fir))
                continue
            if not any(owner in vacc_positions for owner in sector.owners):
                print(label, "no owner is in this vacc", list(sector.owners))
                continue

            airspace = build_airspace(sector, ese_file.sectorlines, config.valid_fir)
            if airspace is None or any(m in sector.local_name for m in GROUND_MARKERS):
                print(label, "is ground, delivery, or invalid")
                continue
            airspaces.append(airspace)

    print(f"Found {len(airspaces)} airspaces")
    vatglasses.save(OUTPUT_FILE, {"airspace": airspaces})
    return 0


if __name__ == "__main__":
    sys.exit(main())
