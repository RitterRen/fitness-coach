"""Shared helpers: repo paths, CSV read/write, .env loading, date parsing.

Personal data lives in a separate private repo cloned to ./private
(override with FITNESS_DATA_DIR). This public repo only holds code.
"""

import csv
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = Path(os.environ.get("FITNESS_DATA_DIR", ROOT / "private")).expanduser()
DATA = PRIVATE / "data"
WEIGHT_CSV = DATA / "body-weight.csv"
SETS_CSV = DATA / "strength" / "sets.csv"
CARDIO_CSV = DATA / "cardio" / "activities.csv"
NUTRITION_CSV = DATA / "nutrition" / "daily.csv"
MEALS_CSV = DATA / "nutrition" / "meals.csv"
MOOD_CSV = DATA / "wellbeing" / "mood.csv"
ENV_FILE = ROOT / ".env"


def rel(path):
    """Path for display, relative to the code repo when possible."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def require_private():
    if not DATA.is_dir():
        raise SystemExit(
            f"No private data repo at {PRIVATE}.\n"
            "Clone it there:  gh repo clone <you>/fitness-data private\n"
            "or start one from the template:  cp -R template private"
        )


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def header_of(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def write_csv(path, rows, fieldnames=None):
    fieldnames = fieldnames or header_of(path)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("STRAVA_")})
    return env


def set_env(key, value):
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


_DATE_RE = re.compile(
    r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*日?"
    r"(?:\s*T?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?)?"
)


def parse_datetime(value):
    """Parse '2026-10-30', '2026/10/30 18:05', '2026年10月30日', or an Excel serial.

    Returns (date, 'HH:MM' or '') or None.
    """
    value = str(value or "").strip()
    if not value:
        return None
    m = _DATE_RE.search(value)
    if m:
        y, mo, d, hh, mm, _ = m.groups()
        t = f"{int(hh):02d}:{mm}" if hh else ""
        return date(int(y), int(mo), int(d)), t
    try:  # Excel serial date (days since 1899-12-30)
        serial = float(value)
        if 20000 < serial < 80000:
            dt = datetime(1899, 12, 30) + timedelta(days=serial)
            t = dt.strftime("%H:%M") if serial % 1 else ""
            return dt.date(), t
    except ValueError:
        pass
    return None


def to_float(value):
    value = str(value or "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(m.group()) if m else None


def fmt_num(x, digits=1):
    if x is None:
        return ""
    s = f"{x:.{digits}f}".rstrip("0").rstrip(".")
    return s
