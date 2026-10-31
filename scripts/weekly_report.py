#!/usr/bin/env python3
"""Summarise the last N days of weight, strength, cardio and nutrition as Markdown.

    python3 scripts/weekly_report.py              # last 7 days
    python3 scripts/weekly_report.py --days 28    # the 28-day training ledger
    python3 scripts/weekly_report.py --end 2026-11-01 --out private/reviews/weekly/2026-W44-data.md
"""

import argparse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from common import CARDIO_CSV, MOOD_CSV, NUTRITION_CSV, SETS_CSV, WEIGHT_CSV, read_csv, require_private, to_float


def in_range(rows, start, end):
    return [r for r in rows if r.get("date") and start <= date.fromisoformat(r["date"]) <= end]


def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def e1rm(weight, reps):
    """Epley estimate; only meaningful for sets of 1–10 reps."""
    return weight * (1 + reps / 30) if weight and 0 < reps <= 10 else None


def weight_section(start, end):
    rows = read_csv(WEIGHT_CSV)
    cur = mean(to_float(r["weight_kg"]) for r in in_range(rows, end - timedelta(days=6), end))
    prev = mean(to_float(r["weight_kg"]) for r in in_range(rows, end - timedelta(days=13), end - timedelta(days=7)))
    period = in_range(rows, start, end)
    out = ["## Body weight", ""]
    if not period:
        return out + ["No weigh-ins in this period.", ""]
    out.append(f"- Weigh-ins: {len(period)} · range {min(to_float(r['weight_kg']) for r in period):.1f}–"
               f"{max(to_float(r['weight_kg']) for r in period):.1f} kg")
    if cur is not None:
        out.append(f"- 7-day average: **{cur:.2f} kg**")
    if cur is not None and prev is not None:
        out.append(f"- Change vs previous 7 days: **{cur - prev:+.2f} kg/week**")
    return out + [""]


def strength_section(start, end):
    rows = in_range(read_csv(SETS_CSV), start, end)
    out = ["## Strength (Xunji)", ""]
    if not rows:
        return out + ["No sets logged in this period.", ""]
    sessions = {(r["date"], r["start_time"]) for r in rows}
    working = [r for r in rows if "热身" not in r["set_type"] and "warm" not in r["set_type"].lower()]
    total = sum((to_float(r["weight_kg"]) or 0) * (to_float(r["reps"]) or 0) for r in working)
    out += [f"- Sessions: {len(sessions)} · working sets: {len(working)} · tonnage: {total:,.0f} kg", ""]

    by_ex = defaultdict(list)
    for r in working:
        by_ex[r["exercise"]].append(r)
    out += ["| Exercise | Sets | Reps | Top set | Best e1RM | Avg RPE |", "|---|---|---|---|---|---|"]
    for ex, sets in sorted(by_ex.items(), key=lambda kv: -len(kv[1])):
        top = max(sets, key=lambda r: (to_float(r["weight_kg"]) or 0, to_float(r["reps"]) or 0))
        best = max((e1rm(to_float(r["weight_kg"]), to_float(r["reps"]) or 0) or 0 for r in sets), default=0)
        rpe = mean(to_float(r["rpe"]) for r in sets)
        out.append(f"| {ex} | {len(sets)} | {sum(int(to_float(r['reps']) or 0) for r in sets)} | "
                   f"{to_float(top['weight_kg']):g} × {top['reps']} | {f'{best:.1f}' if best else '-'} | "
                   f"{f'{rpe:.1f}' if rpe else '-'} |")
    return out + [""]


def cardio_section(start, end):
    rows = in_range(read_csv(CARDIO_CSV), start, end)
    out = ["## Cardio (Strava)", ""]
    if not rows:
        return out + ["No activities in this period.", ""]
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    for t, acts in sorted(by_type.items()):
        km = sum(to_float(a["distance_km"]) or 0 for a in acts)
        mins = sum(to_float(a["moving_min"]) or 0 for a in acts)
        hr = mean(to_float(a["avg_hr"]) for a in acts)
        line = f"- **{t}**: {len(acts)}× · {km:.1f} km · {mins:.0f} min"
        if km > 0.1 and t.lower().endswith("run"):
            line += f" · avg pace {mins / km:.2f} min/km"
        if hr:
            line += f" · avg HR {hr:.0f}"
        out.append(line)
    longest = max(rows, key=lambda r: to_float(r["distance_km"]) or 0)
    out.append(f"- Longest: {longest['date']} {longest['name']} ({longest['distance_km']} km)")
    return out + [""]


def nutrition_section(start, end):
    rows = in_range(read_csv(NUTRITION_CSV), start, end)
    out = ["## Nutrition (Muse)", ""]
    if not rows:
        return out + ["No nutrition data in this period.", ""]
    kcal = mean(to_float(r["calories_kcal"]) for r in rows)
    protein = mean(to_float(r["protein_g"]) for r in rows)
    out.append(f"- Days logged: {len(rows)}")
    if kcal:
        out.append(f"- Average: {kcal:.0f} kcal")
    if protein:
        out.append(f"- Average protein: {protein:.0f} g")
    return out + [""]


def mood_section(start, end):
    rows = in_range(read_csv(MOOD_CSV), start, end)
    out = ["## Mood and recovery (Muse)", ""]
    if not rows:
        return out + ["No mood check-ins in this period.", ""]
    out.append(f"- Check-ins: {len(rows)}")
    for label, col in (("mood", "mood_score"), ("energy", "energy_score"), ("stress", "stress_score")):
        avg = mean(to_float(r[col]) for r in rows)
        if avg is not None:
            out.append(f"- Average {label}: {avg:.1f} / 5")
    sleep = mean(to_float(r["sleep_hours"]) for r in rows)
    if sleep is not None:
        out.append(f"- Average sleep: {sleep:.1f} h")
    tags = defaultdict(int)
    for r in rows:
        for t in filter(None, (t.strip() for t in r["tags"].split(";"))):
            tags[t] += 1
    if tags:
        out.append("- Common tags: " + ", ".join(f"{t} ({n})" for t, n in sorted(tags.items(), key=lambda kv: -kv[1])[:5]))
    return out + [""]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--end", default=date.today().isoformat())
    p.add_argument("--out", type=Path, help="also write the report to this file")
    args = p.parse_args()
    require_private()

    end = date.fromisoformat(args.end)
    start = end - timedelta(days=args.days - 1)
    lines = [f"# Training data: {start} → {end} ({args.days} days)", ""]
    for section in (weight_section, strength_section, cardio_section, nutrition_section, mood_section):
        lines += section(start, end)
    report = "\n".join(lines)
    print(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
