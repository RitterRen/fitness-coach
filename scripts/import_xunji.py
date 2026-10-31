#!/usr/bin/env python3
"""Import Xunji (训记) training exports into data/strength/sets.csv.

Drop .csv or .xlsx exports into inbox/xunji/ and run:

    python3 scripts/import_xunji.py              # import every file in the inbox
    python3 scripts/import_xunji.py path/to.csv  # import specific files
    python3 scripts/import_xunji.py --dry-run    # show what would be imported

Two layouts are understood:
  * one row per set      (date, exercise, weight, reps, ...)
  * one row per exercise with a sets column like "60kg×8, 62.5kg×6, 65×5"

Headers are matched through COLUMN_ALIASES below. If your export uses a header
that is not listed, the script stops and prints the header row so the alias
can be added. Re-importing the same data is safe: rows are deduplicated.
"""

import argparse
import csv
import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from common import PRIVATE, SETS_CSV, rel, require_private, fmt_num, parse_datetime, read_csv, to_float, write_csv

INBOX = PRIVATE / "inbox" / "xunji"
LB_TO_KG = 0.45359237

# Normalised field -> accepted header names (case- and space-insensitive).
COLUMN_ALIASES = {
    "date": ["日期", "训练日期", "时间", "训练时间", "开始时间", "date", "datetime", "start time"],
    "exercise": ["动作", "动作名称", "动作名", "训练动作", "项目", "exercise", "exercise name"],
    "set_no": ["组", "组号", "组序", "第几组", "序号", "set", "set no", "set number"],
    "weight": ["重量", "重量kg", "重量(kg)", "重量（kg）", "负重", "weight", "weight kg", "weight (kg)",
               "重量lb", "重量(lb)", "重量（磅）", "weight lb", "weight (lb)"],
    "reps": ["次数", "个数", "reps", "repetitions", "次"],
    "rpe": ["rpe", "自觉强度", "主观强度", "强度"],
    "set_type": ["组类型", "类型", "set type", "type"],
    "note": ["备注", "笔记", "note", "notes"],
    "sets_text": ["组数据", "训练详情", "详情", "组详情", "sets", "sets detail"],
}

# Matches "60kg×8", "60 x 8", "60*8次", "135lb×5", "自重×12"
SET_TEXT_RE = re.compile(
    r"(?P<w>\d+(?:\.\d+)?|自重|bw)\s*(?P<unit>kg|公斤|lbs?|磅)?\s*[x×X*]\s*(?P<r>\d+)",
    re.IGNORECASE,
)
FIELDS = ["date", "start_time", "exercise", "set_no", "weight_kg", "reps", "rpe", "set_type", "note", "source_file"]
DEDUP_KEY = ("date", "start_time", "exercise", "set_no", "weight_kg", "reps")


def norm(h):
    return re.sub(r"\s+", " ", str(h).strip().lower())


def read_table(path):
    """Return list of rows (lists of strings) from a .csv or .xlsx file."""
    if path.suffix.lower() == ".xlsx":
        return read_xlsx(path)
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"cannot decode {path.name}")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;") if text.strip() else csv.excel
    return [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]


def read_xlsx(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter(f"{{{ns['m']}}}row"):
        cells = {}
        for c in row.findall("m:c", ns):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            idx = 0
            for ch in col:
                idx = idx * 26 + ord(ch) - 64
            v = c.find("m:v", ns)
            if c.get("t") == "s" and v is not None:
                val = shared[int(v.text)]
            elif c.get("t") == "inlineStr":
                val = "".join(t.text or "" for t in c.iter(f"{{{ns['m']}}}t"))
            else:
                val = v.text if v is not None else ""
            cells[idx - 1] = val
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return [r for r in rows if any(str(c).strip() for c in r)]


def map_columns(header):
    lookup = {norm(a): field for field, aliases in COLUMN_ALIASES.items() for a in aliases}
    mapping, unknown = {}, []
    for i, h in enumerate(header):
        field = lookup.get(norm(h))
        if field and field not in mapping:
            mapping[field] = i
        elif not field:
            unknown.append(h)
    lb_weight = "weight" in mapping and re.search(r"lb|磅", norm(header[mapping["weight"]]))
    return mapping, unknown, bool(lb_weight)


def find_header(rows):
    """Exports sometimes start with a title line; use the first row that maps a date + exercise."""
    for i, row in enumerate(rows[:10]):
        mapping, _, _ = map_columns(row)
        if "date" in mapping and "exercise" in mapping:
            return i
    return None


def to_kg(weight, is_lb):
    if weight is None:
        return None
    return weight * LB_TO_KG if is_lb else weight


def parse_file(path):
    rows = read_table(path)
    hi = find_header(rows)
    if hi is None:
        sys.exit(
            f"\n{path.name}: could not find date + exercise columns.\n"
            f"First rows:\n  " + "\n  ".join(" | ".join(r) for r in rows[:3]) +
            "\nAdd the missing header names to COLUMN_ALIASES in scripts/import_xunji.py."
        )
    header = rows[hi]
    mapping, unknown, lb = map_columns(header)
    if "sets_text" not in mapping and not {"weight", "reps"} <= mapping.keys():
        sys.exit(f"\n{path.name}: need weight + reps columns or a sets column. Header: {header}")
    if unknown:
        print(f"  note: ignoring columns {unknown}")

    def get(row, field):
        i = mapping.get(field)
        return row[i].strip() if i is not None and i < len(row) else ""

    out, set_counter = [], {}
    for row in rows[hi + 1:]:
        parsed = parse_datetime(get(row, "date"))
        exercise = get(row, "exercise")
        if not parsed or not exercise:
            continue
        day, start = parsed
        base = {
            "date": day.isoformat(),
            "start_time": start,
            "exercise": exercise,
            "rpe": fmt_num(to_float(get(row, "rpe"))),
            "set_type": get(row, "set_type"),
            "note": get(row, "note"),
            "source_file": path.name,
        }
        if "sets_text" in mapping and get(row, "sets_text"):
            for k, m in enumerate(SET_TEXT_RE.finditer(get(row, "sets_text")), 1):
                w = m.group("w")
                weight = 0.0 if w.lower() in ("自重", "bw") else float(w)
                is_lb = bool(m.group("unit") and re.match(r"lb|磅", m.group("unit"), re.I)) or lb
                out.append({**base, "set_no": str(k), "weight_kg": fmt_num(to_kg(weight, is_lb), 2),
                            "reps": m.group("r")})
            continue
        key = (base["date"], start, exercise)
        set_counter[key] = set_counter.get(key, 0) + 1
        set_no = get(row, "set_no")
        set_no = str(int(to_float(set_no))) if to_float(set_no) is not None else str(set_counter[key])
        reps = to_float(get(row, "reps"))
        if reps is None:
            continue
        out.append({**base, "set_no": set_no,
                    "weight_kg": fmt_num(to_kg(to_float(get(row, "weight")) or 0.0, lb), 2),
                    "reps": str(int(reps))})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*", type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    require_private()

    files = args.files or sorted(f for f in INBOX.iterdir() if f.suffix.lower() in (".csv", ".xlsx"))
    if not files:
        print(f"No .csv/.xlsx files in {rel(INBOX)}/")
        return

    existing = read_csv(SETS_CSV)
    seen = {tuple(r[k] for k in DEDUP_KEY) for r in existing}
    added = []
    for f in files:
        print(f"Reading {f.name}")
        new = [r for r in parse_file(f) if tuple(r[k] for k in DEDUP_KEY) not in seen]
        for r in new:
            seen.add(tuple(r[k] for k in DEDUP_KEY))
        added += new
        print(f"  {len(new)} new sets")

    if not added:
        print("Nothing new.")
        return
    days = sorted({r["date"] for r in added})
    print(f"\n{len(added)} new sets across {len(days)} day(s): {days[0]} → {days[-1]}")
    if args.dry_run:
        for r in added[:15]:
            print(f"  {r['date']} {r['exercise']}  #{r['set_no']}  {r['weight_kg']} kg × {r['reps']}")
        return
    rows = sorted(existing + added, key=lambda r: (r["date"], r["start_time"], r["exercise"], int(r["set_no"] or 0)))
    write_csv(SETS_CSV, rows, FIELDS)
    print(f"Written to {rel(SETS_CSV)}")


if __name__ == "__main__":
    main()
