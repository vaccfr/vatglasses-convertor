#!/usr/bin/env python3
"""Convert the VATGlasses French airspace file into vIFF airblocks GeoJSON.

Uses VATGlasses upstream lf.json by default:
 - local input file can be set with the --input flag
 - output file can be set with the --output flag

vIFF ID naming rules (final id: LF-<ACC>-<NAME>[/<MIN>-<MAX>]):
  1. <ACC> comes from the VATGlasses group: LFFF -> PAR (override), LFxx -> xx.
  2. <NAME> is the VATGlasses id uppercased, the standalone word UAC removed,
     hyphens glued, spaces turned into underscores, anything outside
     [A-Z0-9._-] dropped. Nothing is invented; source typos are kept.
  3. /<MIN>-<MAX> (3-digit FLs) is appended only when one (ACC, NAME) covers
     more than one vertical band; pieces sharing name and band are merged
     into one MultiPolygon.
  4. Volumes whose ceiling is below --min-ceiling (default FL014, aerodrome
     surface polygons) are dropped.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from typing import IO

DEFAULT_SOURCE = "https://raw.githubusercontent.com/lennycolton/vatglasses-data/refs/heads/main/data/lf.json"
FIR_PREFIX = "LF"
ACC_OVERRIDES = {"LFFF": "PAR"}
DEFAULT_MIN_CEILING = 14
ID_RE = re.compile(r"^LF-[A-Z0-9]+-[A-Z0-9._-]+(/\d{3}-\d{3})?$")

_COORD_RES = {
    digits: re.compile(rf"^(-?)(\d{{{digits}}})(\d{{2}})(\d{{2}}(?:\.\d+)?)$")
    for digits in (2, 3)
}


def acc_token(group: str) -> str:
    """Owning ACC token from the VATGlasses group (rule 1)."""
    group = group.strip().upper()
    if group in ACC_OVERRIDES:
        return ACC_OVERRIDES[group]
    if re.fullmatch(r"LF[A-Z]{2}", group):
        return group[2:]
    token = re.sub(r"[^A-Z0-9]", "", group)
    if not token:
        raise ValueError(f"group {group!r} normalises to an empty ACC token")
    return token


def sector_name(vg_id: str) -> str:
    """Normalised sector name from the VATGlasses id (rule 2)."""
    s = vg_id.upper().strip()
    s = re.sub(r"(?<![A-Z0-9])UAC(?![A-Z0-9])", " ", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"[^A-Z0-9._-]", "", s)
    s = re.sub(r"_{2,}", "_", s).strip("_-")
    if not s:
        raise ValueError(f"airspace {vg_id!r} normalises to an empty name")
    return s


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


def convert(data: dict, min_ceiling: int) -> tuple[list[dict], int]:
    """Build vIFF features from VATGlasses data; return (features, dropped_count)."""
    airspaces = data.get("airspace") if isinstance(data, dict) else None
    if not isinstance(airspaces, list):
        raise ValueError("input has no 'airspace' list")

    dropped = 0
    volumes: dict[tuple[str, str, int, int], list[list[list[float]]]] = {}
    for airspace in airspaces:
        vg_id = airspace["id"]
        acc = acc_token(airspace["group"])
        name = sector_name(vg_id)
        for sector in airspace.get("sectors", []):
            # Missing bounds: assume VATGlasses' implied full column (unverified).
            lo = int(sector.get("min", 0))
            hi = int(sector.get("max", 999))
            if hi < min_ceiling:
                dropped += 1
                continue
            if lo > hi:
                raise ValueError(f"{vg_id}: min FL{lo} above max FL{hi}")
            volumes.setdefault((acc, name, lo, hi), []).append(ring(sector["points"], vg_id))

    bands: dict[tuple[str, str], int] = defaultdict(int)
    for acc, name, _, _ in volumes:
        bands[(acc, name)] += 1

    features = []
    for (acc, name, lo, hi), rings in volumes.items():
        fid = f"{FIR_PREFIX}-{acc}-{name}"
        if bands[(acc, name)] > 1:
            fid += f"/{lo:03d}-{hi:03d}"
        features.append({
            "type": "Feature",
            "properties": {"id": fid, "minFL": lo, "maxFL": hi},
            "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
        })

    ids = [f["properties"]["id"] for f in features]
    bad = [i for i in ids if not ID_RE.match(i)]
    if bad:
        raise ValueError(f"invalid ids: {', '.join(bad)}")
    seen: set[str] = set()
    dupes = sorted({i for i in ids if i in seen or seen.add(i)})
    if dupes:
        raise ValueError(f"duplicate ids: {', '.join(dupes)}")

    features.sort(key=lambda f: f["properties"]["id"])
    return features, dropped


def dump(features: list[dict], fp: IO[str]) -> None:
    """Write a FeatureCollection with one feature per line."""
    body = ",\n".join(
        "    " + json.dumps(f, separators=(",", ":"), ensure_ascii=False) for f in features
    )
    fp.write('{\n  "type": "FeatureCollection",\n  "features": [\n')
    fp.write(body)
    fp.write("\n  ]\n}\n")


def load(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(source, encoding="utf-8") as fp:
        return json.load(fp)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vg2viff", description="Convert VATGlasses LF airspace to vIFF airblocks.geojson."
    )
    parser.add_argument("-i", "--input", default=DEFAULT_SOURCE,
                        help="VATGlasses JSON file path or http(s) URL (default: upstream lf.json)")
    parser.add_argument("-o", "--output", default="airblocks.geojson",
                        help="output GeoJSON path, '-' for stdout (default: airblocks.geojson)")
    parser.add_argument("--min-ceiling", type=int, default=DEFAULT_MIN_CEILING,
                        help="skip volumes whose max FL is below this (default: %(default)s; 0 keeps all)")
    args = parser.parse_args(argv)

    try:
        features, dropped = convert(load(args.input), args.min_ceiling)
        if args.output == "-":
            dump(features, sys.stdout)
        else:
            with open(args.output, "w", encoding="utf-8") as fp:
                dump(features, fp)
    except (ValueError, OSError, urllib.error.URLError) as exc:
        # json.JSONDecodeError is a ValueError subclass.
        print(f"vg2viff: error: {exc}", file=sys.stderr)
        return 1

    suffixed = sum(1 for f in features if "/" in f["properties"]["id"])
    print(
        f"wrote {len(features)} airblocks to {args.output} "
        f"({dropped} surface volumes below FL{args.min_ceiling:03d} dropped, "
        f"{suffixed} ids with band suffix)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
