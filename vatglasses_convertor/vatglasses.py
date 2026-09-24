"""VATGlasses JSON I/O and geometry helpers.

Standard library only, so that ``export_viff.py`` keeps working without third-party packages.
"""

import json
import re
import urllib.request
from pathlib import Path

DEFAULT_MIN_FL = 0
DEFAULT_MAX_FL = 999  # a sector without "max" is unbounded upwards

_COORD_RES = {
    digits: re.compile(rf"^(-?)(\d{{{digits}}})(\d{{2}})(\d{{2}}(?:\.\d+)?)$")
    for digits in (2, 3)
}


def load(source: str | Path) -> dict:
    """Load a JSON document from a file path or an http(s) URL."""
    source = str(source)
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(source, encoding="utf-8") as fp:
        return json.load(fp)


def save(path: Path, document: dict, *, ensure_ascii: bool = True) -> None:
    """Write ``document`` as 2-space indented JSON, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(document, fp, indent=2, ensure_ascii=ensure_ascii)
    print(f"Wrote {path}")


def parse_coord(value: str, deg_digits: int) -> float:
    """Parse a VATGlasses [-]D{deg_digits}MMSS[.s] string into decimal degrees."""
    m = _COORD_RES[deg_digits].match(str(value).strip())
    if not m:
        raise ValueError(f"bad coordinate {value!r}")
    sign, deg, mins, secs = m.groups()
    result = int(deg) + int(mins) / 60 + float(secs) / 3600
    return -result if sign == "-" else result


def ring(points: list, where: str) -> list[list[float]]:
    """Convert VATGlasses [lat, lon] points into a closed GeoJSON [lon, lat] ring."""
    try:
        out = [[parse_coord(lon, 3), parse_coord(lat, 2)] for lat, lon in points]
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{where}: {exc}") from None
    if out and out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:
        raise ValueError(f"{where}: ring has fewer than 4 points")
    return out


def sector_levels(sector: dict) -> tuple[int, int]:
    """(min, max) flight levels of an airspace sector, with VATGlasses defaults."""
    return int(sector.get("min", DEFAULT_MIN_FL)), int(sector.get("max", DEFAULT_MAX_FL))
