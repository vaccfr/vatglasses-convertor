"""EuroScope sector file (``.ese``) parsing and ESE input selection.

Only the parts the converters need are parsed:

- ``[POSITIONS]`` lines: ``callsign:radio name:frequency:id:middle letter:prefix:suffix:...``.
  Position IDs are local to one ESE file.
- ``SECTOR:FIR·NAME·lo·hi:low_ft:high_ft`` blocks with their ``OWNER:``, ``BORDER:`` and
  ``ACTIVE:`` lines. A block ends at a blank line or at the next ``SECTOR:`` header.
- ``SECTORLINE:id`` blocks with their ``COORD:lat:lon`` lines. IDs are local to one ESE file.
"""

import argparse
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import COMBINED_ESE_FILE, FIR_ESE_FILES

NAME_SEPARATOR = "\u00b7"  # "·" between the parts of a SECTOR name
POSITION_FIELDS = 7  # callsign .. suffix; later fields are not used


@dataclass(frozen=True)
class Position:
    callsign: str  # e.g. "PAR_CTR"
    radio_name: str  # e.g. "Paris Control"
    frequency: str
    id: str  # sector owner ID, local to the ESE file
    prefix: str  # e.g. "LFPG"
    suffix: str  # position type, e.g. "CTR", "APP", "TWR"

    @classmethod
    def parse(cls, line: str) -> "Position | None":
        """Parse a ``[POSITIONS]`` line; return None for comments and short lines."""
        if line.lstrip().startswith(";"):
            return None
        fields = [field.strip() for field in line.rstrip("\r\n").split(":")]
        if len(fields) < POSITION_FIELDS:
            return None
        callsign, radio_name, frequency, position_id, _, prefix, suffix = fields[
            :POSITION_FIELDS
        ]
        return cls(callsign, radio_name, frequency, position_id, prefix, suffix)


@dataclass(frozen=True)
class Sector:
    name: str  # full "FIR·NAME·lo·hi" name
    low_ft: int
    high_ft: int
    owners: tuple[str, ...]  # topdown priority: most specific position first
    borders: tuple[str, ...]  # SECTORLINE IDs
    active: tuple[tuple[str, str], ...]  # (airport ICAO, runway) from ACTIVE lines

    @property
    def fir(self) -> str:
        return self.name.split(NAME_SEPARATOR, 1)[0]

    @property
    def local_name(self) -> str:
        """Sector name without the FIR and level parts, e.g. "BIARRITZ CTR"."""
        return self.name.split(NAME_SEPARATOR)[1]


Point = tuple[str, str]  # raw (latitude, longitude), e.g. ("N043.28.09.282", "W001.31.15.944")


@dataclass(frozen=True)
class EseFile:
    path: Path
    # FIR the file belongs to (its stem, e.g. LFBB) or None for combined files.
    source_fir: str | None
    positions: tuple[Position, ...]
    # Sectors of source_fir only when set: FIR files also copy their neighbours' sectors.
    sectors: tuple[Sector, ...]
    sectorlines: dict[str, tuple[Point, ...]]


def load(path: Path, valid_firs: Iterable[str]) -> EseFile:
    print(f"Loading ESE file {path}")
    with open(path, encoding="utf-8-sig") as file:
        lines = file.readlines()

    source_fir = path.stem.upper()
    if source_fir not in valid_firs:
        source_fir = None

    sectors = parse_sectors(lines)
    if source_fir is not None:
        sectors = [sector for sector in sectors if sector.fir == source_fir]

    return EseFile(
        path=path,
        source_fir=source_fir,
        positions=tuple(parse_positions(lines)),
        sectors=tuple(sectors),
        sectorlines=parse_sectorlines(lines),
    )


def parse_positions(lines: Iterable[str]) -> list[Position]:
    positions = []
    in_block = False
    for line in lines:
        if line.startswith("[POSITIONS]"):
            in_block = True
        elif line.startswith("["):
            in_block = False
        elif in_block and (position := Position.parse(line)) is not None:
            positions.append(position)
    return positions


def parse_sectors(lines: Iterable[str]) -> list[Sector]:
    """Parse SECTOR blocks; blocks without an OWNER line are skipped."""
    sectors = []
    for header, body in _blocks(lines, "SECTOR:"):
        owners = _first_line_fields(body, "OWNER:")
        if owners is None:
            continue
        _, name, low_ft, high_ft = header.split(":")[:4]
        sectors.append(
            Sector(
                name=name,
                low_ft=int(low_ft),
                high_ft=int(high_ft),
                owners=owners,
                borders=_first_line_fields(body, "BORDER:") or (),
                active=tuple(
                    (fields[1].strip(), fields[2].strip())
                    for fields in _keyword_fields(body, "ACTIVE:")
                    if len(fields) >= 3
                ),
            )
        )
    return sectors


def parse_sectorlines(lines: Iterable[str]) -> dict[str, tuple[Point, ...]]:
    """Map SECTORLINE IDs to their points; a later definition of an ID wins."""
    sectorlines = {}
    for header, body in _blocks(lines, "SECTORLINE:"):
        # Headers can carry an inline comment: "SECTORLINE:1894 ; GLO18288-GLO36927".
        line_id = header.split(":", 1)[1].split(";", 1)[0].strip()
        sectorlines[line_id] = tuple(
            (fields[1], fields[2]) for fields in _keyword_fields(body, "COORD:")
        )
    return sectorlines


def _blocks(lines: Iterable[str], keyword: str) -> Iterator[tuple[str, list[str]]]:
    """Yield (header, body) for blocks starting with ``keyword``.

    A block ends at a blank line or at the next ``keyword`` header. Lines are stripped
    and comment lines dropped.
    """
    header = None
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if line.startswith(keyword):
            if header is not None:
                yield header, body
            header, body = stripped, []
        elif header is None:
            continue
        elif not stripped:
            yield header, body
            header = None
        elif not stripped.startswith(";"):
            body.append(stripped)
    if header is not None:
        yield header, body


def _keyword_fields(body: Iterable[str], keyword: str) -> Iterator[list[str]]:
    """``:``-separated fields (keyword included) of every line starting with ``keyword``."""
    for line in body:
        if line.startswith(keyword):
            yield line.split(":")


def _first_line_fields(body: Iterable[str], keyword: str) -> tuple[str, ...] | None:
    """Non-empty values of the first ``keyword`` line, or None if there is none."""
    for fields in _keyword_fields(body, keyword):
        return tuple(value for field in fields[1:] if (value := field.strip()))
    return None


def parse_input_files(description: str, argv: Sequence[str] | None = None) -> list[Path]:
    """Return the ESE files to process, from the command line or the default inputs.

    Precedence: positional paths, then all per-FIR files if they all exist, then the
    combined ``inputs/LFXX.ese``.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "ese_files",
        nargs="*",
        type=Path,
        metavar="ESE_FILE",
        help="ESE files to merge, in order (default: "
        + ", ".join(map(str, FIR_ESE_FILES))
        + f" if all exist, else {COMBINED_ESE_FILE})",
    )
    args = parser.parse_args(argv)

    if args.ese_files:
        input_files = args.ese_files
    elif all(path.is_file() for path in FIR_ESE_FILES):
        input_files = list(FIR_ESE_FILES)
    elif COMBINED_ESE_FILE.is_file():
        input_files = [COMBINED_ESE_FILE]
    else:
        expected = ", ".join(str(path) for path in FIR_ESE_FILES)
        parser.error(
            f"No ESE input found. Add {COMBINED_ESE_FILE}, add all of "
            f"{expected}, or pass ESE paths on the command line."
        )

    missing = [str(path) for path in input_files if not path.is_file()]
    if missing:
        parser.error("ESE input file(s) not found: " + ", ".join(missing))

    return input_files
