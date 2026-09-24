"""Generate outputs/positions.json, the VATGlasses "positions" section, from ESE files.

Also updates the per-callsign colour cache config/colors.yml.
"""

import random
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from vatglasses_convertor import ese, vatglasses
from vatglasses_convertor.config import COLORS_FILE, OUTPUTS_DIR, ColorRule, load_config

OUTPUT_FILE = OUTPUTS_DIR / "positions.json"
EXCLUDED_TYPES = frozenset({"ATIS", "GND", "RMP", "DEL"})
# Home FIR of area-control callsign prefixes that are not an FIR code.
AREA_CONTROL_HOME_FIR = {"PAR": "LFFF", "LFFM": "LFFF"}
COLOR_VARIANCE = 30


def home_fir(callsign: str, valid_fir: Sequence[str]) -> str | None:
    """FIR file that owns the definition of an area-control callsign, if any."""
    prefix = callsign.split("_", 1)[0]
    if prefix in AREA_CONTROL_HOME_FIR:
        return AREA_CONTROL_HOME_FIR[prefix]
    return prefix if prefix in valid_fir else None


def collect_positions(
    ese_files: Sequence[ese.EseFile], callsign_re: re.Pattern, valid_fir: Sequence[str]
) -> dict[str, ese.Position]:
    """vACC positions keyed by ID; files are applied in order, the last definition wins."""
    positions = {}
    for ese_file in ese_files:
        source_fir = ese_file.source_fir
        allowed_ids = None
        if source_fir is not None:
            allowed_ids = {owner for sector in ese_file.sectors for owner in sector.owners}
            print(
                f"  Restricting positions to {len(allowed_ids)} "
                f"owner IDs used by {source_fir} sectors"
            )

        count = 0
        for position in ese_file.positions:
            if not callsign_re.search(position.callsign):
                continue
            if allowed_ids is not None and position.id not in allowed_ids:
                continue
            # Area-control definitions are copied into neighbouring FIR files
            # for coordination. Keep them only from their home file.
            home = home_fir(position.callsign, valid_fir)
            if source_fir is not None and home is not None and home != source_fir:
                continue
            # Some FIRs intentionally reuse short IDs such as UN, X, or Z.
            positions[position.id] = position
            count += 1
        print(f"  Found {count} matching positions")
    return positions


def deduplicate(positions: dict[str, ese.Position]) -> dict[str, ese.Position]:
    """Keep one position per (radio name, frequency).

    VATGlasses cannot use several position IDs with the same displayed callsign and
    frequency. The least specialised callsign wins, e.g. PAR_CTR over PAR_TB_CTR.
    """
    best: dict[tuple[str, str], ese.Position] = {}
    for position in positions.values():
        key = (position.radio_name, position.frequency)
        current = best.get(key)
        if current is None or _specificity(position) < _specificity(current):
            best[key] = position
    return {position.id: position for position in best.values()}


def _specificity(position: ese.Position) -> tuple[int, str]:
    return position.callsign.count("_"), position.callsign


def load_color_cache(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        print(f"Color file {path} does not exist, will create new one")
        return []
    print(f"Loading color file {path}")
    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file) or []


def resolve_color(
    callsign: str, cache: list[dict[str, str]], rules: Sequence[ColorRule]
) -> str | None:
    """Cached colour of ``callsign``, else derive one from ``rules`` and cache it.

    LFXX_CTR gets the rule colour; sub-sectors such as LFXX_X_CTR get a random shade.
    """
    for entry in cache:
        if entry["callsign"] == callsign:
            return entry["color"]
    for rule in rules:
        if re.search(rule.pattern, callsign):
            color = rule.color
            if callsign.count("_") >= 2:
                color = randomize_color(color)
            cache.append({"callsign": callsign, "color": color})
            return color
    return None


def randomize_color(color_hex: str, variance: int = COLOR_VARIANCE) -> str:
    channels = (int(color_hex[i : i + 2], 16) for i in (1, 3, 5))
    r, g, b = (_clamp(c + random.randint(-variance, variance)) for c in channels)
    return f"#{r:02x}{g:02x}{b:02x}"


def _clamp(value: int) -> int:
    return max(0, min(value, 255))


def main(argv: Sequence[str] | None = None) -> int:
    config = load_config()
    colors = load_color_cache(COLORS_FILE)
    input_files = ese.parse_input_files(
        "Generate VATGlasses positions from one or more ESE files.", argv
    )
    ese_files = [ese.load(path, config.valid_fir) for path in input_files]

    positions = collect_positions(
        ese_files, re.compile(config.valid_callsign), config.valid_fir
    )
    print(f"Found {len(positions)} unique positions across all input files")

    canonical = deduplicate(positions)
    print(
        f"Kept {len(canonical)} canonical callsign/frequency definitions "
        f"({len(positions) - len(canonical)} duplicate aliases removed)"
    )

    output = {}
    missing_color = False
    for position in canonical.values():
        if position.suffix in EXCLUDED_TYPES:
            continue
        color = resolve_color(position.callsign, colors, config.colors)
        if color is None:
            print(f"Error: no colors defined for {position.id} ({position.callsign})")
            missing_color = True
            continue
        output[position.id] = {
            "callsign": position.radio_name,
            "frequency": position.frequency,
            "type": position.suffix,
            "pre": [position.prefix],
            "colours": [{"hex": color}],
        }

    if missing_color:
        return 1
    print("Was able to find colours for all positions")

    print(f"Updating color file {COLORS_FILE}")
    with open(COLORS_FILE, "w", encoding="utf-8") as file:
        yaml.dump(colors, file)

    vatglasses.save(OUTPUT_FILE, {"positions": output})
    return 0


if __name__ == "__main__":
    sys.exit(main())
