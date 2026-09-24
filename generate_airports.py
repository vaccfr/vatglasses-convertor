"""Generate outputs/airports.json, the VATGlasses "airports" section.

Airports come from VATSpy.dat; their topdown order comes from the ESE sectors, overridden
by inputs/airports.json. Airports without topdown are listed in outputs/missing_topdown.txt.
"""

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import requests

from vatglasses_convertor import ese, vatglasses
from vatglasses_convertor.config import MANUAL_AIRPORTS_FILE, OUTPUTS_DIR, load_config

VATSPY_DAT_URL = "https://raw.githubusercontent.com/vatsimnetwork/vatspy-data-project/refs/heads/master/VATSpy.dat"
OUTPUT_FILE = OUTPUTS_DIR / "airports.json"
MISSING_TOPDOWN_FILE = OUTPUTS_DIR / "missing_topdown.txt"


def position_airports(
    ese_file: ese.EseFile, callsign_re: re.Pattern, airport_re: re.Pattern
) -> dict[str, str]:
    """Map vACC position IDs to the airport ICAO in their prefix field."""
    return {
        position.id: position.prefix
        for position in ese_file.positions
        if callsign_re.search(position.callsign) and airport_re.match(position.prefix)
    }


def topdown_from_ese(
    ese_file: ese.EseFile, callsign_re: re.Pattern, airport_re: re.Pattern
) -> dict[str, list[str]]:
    """Airport ICAO -> owner list of the first sector owned by one of its positions."""
    airport_of = position_airports(ese_file, callsign_re, airport_re)
    print(f"Found {len(airport_of)} position -> airport mappings")

    topdown: dict[str, list[str]] = {}
    for sector in ese_file.sectors:
        for owner in sector.owners:
            icao = airport_of.get(owner)
            if icao is not None and icao not in topdown:
                topdown[icao] = list(sector.owners)
                print(f"ESE TOPDOWN: {icao} -> {topdown[icao]}")

    print(f"Found {len(topdown)} topdown chains from ESE")
    return topdown


def load_manual_topdown(path: Path) -> dict[str, list[str]]:
    """Manual topdown overrides.

    Preferred format: ``[{"icao": "LFAC", "topdown": ["ACI", "QW", ...]}, ...]``.
    Legacy format: ``{"airports": {"LFAC": {"topdown": [...]}}}``.
    """
    if not path.exists():
        print(f"No manual airports file found at {path}")
        return {}

    print(f"Loading manual topdown data from {path}")
    data = vatglasses.load(path)

    if isinstance(data, list):
        entries = ((item.get("icao"), item.get("topdown")) for item in data)
    elif isinstance(data, dict):
        entries = (
            (icao, airport.get("topdown"))
            for icao, airport in data.get("airports", {}).items()
        )
    else:
        entries = ()
    manual = {icao: topdown for icao, topdown in entries if icao and topdown}

    print(f"Loaded {len(manual)} manual topdown chains")
    return manual


def download_vatspy(url: str) -> str:
    print(f"Downloading VATSPY data from {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def build_airports(
    vatspy_data: str, airport_re: re.Pattern, topdown: dict[str, list[str]]
) -> tuple[dict[str, dict], list[tuple[str, str]]]:
    """Return (airports keyed by ICAO, [(icao, name)] of airports without topdown)."""
    airports = {}
    missing = []
    for line in vatspy_data.splitlines():
        fields = line.split("|")
        if len(fields) <= 5 or not airport_re.match(fields[0]):
            continue

        icao, name, lat, lon = fields[:4]
        airport = {"callsign": name, "coord": [float(lat), float(lon)]}
        if icao in topdown:
            airport["default"] = False
            airport["topdown"] = topdown[icao]
        else:
            missing.append((icao, name))
        airports[icao] = airport
    return airports, missing


def write_missing_topdown(path: Path, missing: Sequence[tuple[str, str]]) -> None:
    """One paste-ready inputs/airports.json entry per line (the file is not valid JSON)."""
    with open(path, "w", encoding="utf-8") as outfile:
        outfile.write("# Airports missing topdown\n")
        outfile.write("# Add these to inputs/airports.json if needed.\n\n")
        for icao, name in missing:
            entry = {"icao": icao, "callsign": name, "topdown": ["Uncontrolled(?)"]}
            outfile.write(json.dumps(entry, ensure_ascii=False) + ",\n")
    print(f"Wrote {path}")


def main(argv: Sequence[str] | None = None) -> int:
    config = load_config()
    input_files = ese.parse_input_files(
        "Generate VATGlasses airports from one or more ESE files.", argv
    )
    callsign_re = re.compile(config.valid_callsign)
    airport_re = re.compile(config.valid_airport)

    # 1. Topdown from the ESE files; later files win.
    topdown = {}
    for path in input_files:
        ese_file = ese.load(path, config.valid_fir)
        topdown.update(topdown_from_ese(ese_file, callsign_re, airport_re))

    # 2. Manual inputs/airports.json wins over ESE.
    for icao, chain in load_manual_topdown(MANUAL_AIRPORTS_FILE).items():
        topdown[icao] = chain
        print(f"MANUAL TOPDOWN: {icao} -> {chain}")
    print(f"Total topdown airport chains: {len(topdown)}")

    # 3. Airport list from VATSpy.
    airports, missing = build_airports(download_vatspy(VATSPY_DAT_URL), airport_re, topdown)
    print(f"Found {len(airports)} airports")

    vatglasses.save(OUTPUT_FILE, {"airports": airports}, ensure_ascii=False)
    write_missing_topdown(MISSING_TOPDOWN_FILE, missing)
    print(f"Airports without topdown: {len(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
