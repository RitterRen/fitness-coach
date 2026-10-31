#!/usr/bin/env python3
"""Log a body-weight reading and show the 7-day trend.

    python3 scripts/log_weight.py 72.4
    python3 scripts/log_weight.py 72.4 --date 2026-10-30 --note "after travel"
    python3 scripts/log_weight.py --show
"""

import argparse
from datetime import date, timedelta

from common import WEIGHT_CSV, fmt_num, read_csv, require_private, write_csv


def avg_between(rows, start, end):
    vals = [float(r["weight_kg"]) for r in rows if start <= date.fromisoformat(r["date"]) <= end]
    return sum(vals) / len(vals) if vals else None


def trend(rows, today):
    cur = avg_between(rows, today - timedelta(days=6), today)
    prev = avg_between(rows, today - timedelta(days=13), today - timedelta(days=7))
    return cur, prev


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("weight", nargs="?", type=float, help="weight in kg")
    p.add_argument("--date", default=date.today().isoformat())
    p.add_argument("--note", default="")
    p.add_argument("--show", action="store_true", help="only print the trend")
    args = p.parse_args()
    require_private()

    rows = read_csv(WEIGHT_CSV)
    day = date.fromisoformat(args.date)

    if args.weight is not None and not args.show:
        if not 25 <= args.weight <= 300:
            p.error("weight looks wrong — expected kg")
        rows = [r for r in rows if r["date"] != day.isoformat()]
        rows.append({"date": day.isoformat(), "weight_kg": fmt_num(args.weight, 2), "note": args.note,
                     "source": "manual"})
        rows.sort(key=lambda r: r["date"])
        write_csv(WEIGHT_CSV, rows)
        print(f"Logged {fmt_num(args.weight, 2)} kg on {day}")
    elif not rows:
        print("No weigh-ins yet.")
        return

    cur, prev = trend(rows, day)
    if cur is not None:
        line = f"7-day average: {cur:.2f} kg"
        if prev is not None:
            line += f"  (previous 7 days: {prev:.2f} kg, change {cur - prev:+.2f} kg/week)"
        print(line)


if __name__ == "__main__":
    main()
