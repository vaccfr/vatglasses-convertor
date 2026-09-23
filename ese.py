"""Shared EuroScope sector-file (ESE) helpers for the generate_* scripts.

Position IDs (field [3] of a ``[POSITIONS]`` line) are local to each ESE file:
``PAR_CTR`` is ``PAR`` in LFFF.ese, ``P`` in LFEE.ese and ``FF`` in LFBB.ese,
while ``P`` in LFBB.ese is ``LFBB_P_CTR``. ``PositionIds`` assigns every vACC
callsign a single output ID and translates each file's OWNER lists into it, so
positions.json, airspace owners and airport topdowns all agree.

Standard library only.
"""

import re
from pathlib import Path

AREA_CONTROL_HOME = {"PAR": "LFFF", "LFFM": "LFFF"}


def load(path: Path) -> list[str]:
    """Read an ESE file as lines."""
    with open(path, "r", encoding="utf-8-sig") as file:
        return file.readlines()


def source_fir(path: Path, valid_fir: list[str]) -> str | None:
    """FIR whose own sectors a per-FIR file is authoritative for, if any."""
    fir = path.stem.upper()
    return fir if fir in valid_fir else None


def read_positions(ese_data: list[str], valid_callsign: str) -> dict[str, list[str]]:
    """Return ``{local ID: fields}`` for vACC positions; first definition wins."""
    positions = {}
    block = False
    for line in ese_data:
        if line.startswith("[POSITIONS]"):
            block = True
        elif block and line.startswith("["):
            block = False
        elif block and not line.startswith(";") and re.search(valid_callsign, line):
            parts = [part.strip() for part in line.rstrip("\r\n").split(":")]
            if len(parts) > 6:
                positions.setdefault(parts[3], parts)
    return positions


def read_owner_ids(ese_data: list[str], fir: str | None) -> set[str]:
    """Local owner IDs of the sectors belonging to ``fir`` (all sectors if None)."""
    owner_ids = set()
    in_sector = False
    for line in ese_data:
        if line.startswith("SECTOR:"):
            sector_fir = line.split(":", 2)[1].split("·", 1)[0]
            in_sector = fir is None or sector_fir == fir
        elif in_sector and line.startswith("OWNER:"):
            owner_ids.update(o.strip() for o in line.strip().split(":")[1:] if o.strip())
        elif in_sector and not line.strip():
            in_sector = False
    return owner_ids


def home_fir(callsign: str, valid_fir: list[str]) -> str | None:
    """FIR file that owns an area-control callsign's definition, if any."""
    prefix = callsign.split("_", 1)[0]
    if prefix in AREA_CONTROL_HOME:
        return AREA_CONTROL_HOME[prefix]
    return prefix if prefix in valid_fir else None


class PositionIds:
    """Global position IDs for a set of ESE files.

    Attributes:
        definitions: ``{output ID: fields}`` for every position referenced by an
            in-scope sector, in file order. Fields come from the callsign's home
            file when available.
    """

    def __init__(self, ese_files: dict[Path, list[str]], valid_fir: list[str], valid_callsign: str):
        self._local = {path: read_positions(data, valid_callsign) for path, data in ese_files.items()}

        # Pick one definition per callsign: home file, then a file whose own
        # sectors reference it, then the last file (legacy last-wins order).
        chosen = {}
        referenced = set()
        for index, (path, data) in enumerate(ese_files.items()):
            fir = source_fir(path, valid_fir)
            owners = read_owner_ids(data, fir)
            for line_index, (local_id, parts) in enumerate(self._local[path].items()):
                callsign = parts[0]
                is_referenced = local_id in owners
                if is_referenced:
                    referenced.add(callsign)
                rank = (fir is not None and fir == home_fir(callsign, valid_fir), is_referenced, index)
                if callsign not in chosen or rank >= chosen[callsign][0]:
                    chosen[callsign] = (rank, (index, line_index), parts)

        # VATGlasses cannot tell apart positions sharing a radio name and
        # frequency: keep the least specialised callsign (PAR_CTR over
        # PAR_TB_CTR) and map the others onto it.
        canonical = {}
        for callsign, (_, _, parts) in chosen.items():
            key = (parts[1], parts[2])
            if key not in canonical or (callsign.count("_"), callsign) < (
                canonical[key].count("_"),
                canonical[key],
            ):
                canonical[key] = callsign
        target = {c: canonical[(p[1], p[2])] for c, (_, _, p) in chosen.items()}

        # Output IDs keep each definition's local ID. On a clash between
        # distinct positions the latest file keeps the bare ID and the others
        # are qualified with their FIR (LFBB_N_CTR -> BB.N).
        kept = sorted({target[c] for c in referenced}, key=lambda c: chosen[c][1])
        by_id = {}
        for callsign in kept:
            by_id.setdefault(chosen[callsign][2][3], []).append(callsign)
        output_id = {}
        for local_id, callsigns in by_id.items():
            output_id[callsigns[-1]] = local_id
            for callsign in callsigns[:-1]:
                fir = home_fir(callsign, valid_fir) or list(ese_files)[chosen[callsign][1][0]].stem.upper()
                output_id[callsign] = f"{fir[2:]}.{local_id}"
        if len(set(output_id.values())) != len(output_id):
            raise ValueError(f"position ID clash after qualification: {output_id}")

        self._ids = {c: output_id[target[c]] for c in chosen if target[c] in output_id}
        self.definitions = {output_id[c]: chosen[c][2] for c in kept}

    def translate(self, path: Path, owners: list[str]) -> list[str]:
        """Map a file's local owner IDs to output IDs.

        Owners that are not vACC positions (foreign units such as LON_CTR) are
        dropped; duplicates created by aliases keep their first position.
        """
        result = []
        for owner in owners:
            parts = self._local[path].get(owner)
            owner_id = self._ids.get(parts[0]) if parts else None
            if owner_id is not None and owner_id not in result:
                result.append(owner_id)
        return result
