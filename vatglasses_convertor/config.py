"""Repository paths and ``config/config.yml`` loading.

All paths are relative: the scripts are meant to be run from the repository root.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_FILE = Path("config/config.yml")
COLORS_FILE = Path("config/colors.yml")

INPUTS_DIR = Path("inputs")
COMBINED_ESE_FILE = INPUTS_DIR / "LFXX.ese"
# Processing order matters: later files win when definitions collide.
FIR_ESE_FILES = tuple(
    INPUTS_DIR / f"{fir}.ese" for fir in ("LFBB", "LFEE", "LFFF", "LFMM", "LFRR")
)
MANUAL_AIRPORTS_FILE = INPUTS_DIR / "airports.json"

OUTPUTS_DIR = Path("outputs")


@dataclass(frozen=True)
class ColorRule:
    """Default colour for callsigns matching ``pattern`` (``re.search``)."""

    pattern: str
    color: str


@dataclass(frozen=True)
class Config:
    valid_fir: tuple[str, ...]
    valid_callsign: str
    valid_airport: str
    colors: tuple[ColorRule, ...]


def load_config(path: Path = CONFIG_FILE) -> Config:
    print(f"Loading config file {path}")
    with open(path, encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    settings = raw["config"]
    return Config(
        valid_fir=tuple(settings["valid_fir"]),
        valid_callsign=settings["valid_callsign"],
        valid_airport=settings["valid_airport"],
        colors=tuple(
            ColorRule(pattern=rule["callsign"], color=rule["color"])
            for rule in raw.get("colors") or []
        ),
    )
