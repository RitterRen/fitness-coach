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

from common import (BODY_COMP_CSV, CARDIO_CSV, MOOD_CSV, NUTRITION_CSV, SETS_CSV, WEIGHT_CSV, read_csv,
                    require_private, to_float)
from race_fitness import KM_PER_MILE, RACES, best_effort, fmt_time, load_targets, race_time, vdot


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
    days = (end - start).days + 1
    estimated = sum(r["note"].lower().startswith("estimate") for r in rows)
    incomplete = sum("incomplete" in r["note"].lower() for r in rows)
    line = f"- Days logged: {len(rows)} of {days}"
    if estimated:
        line += f" · {estimated} estimated"
    if incomplete:
        line += f" · {incomplete} incomplete"
    out.append(line)
    if kcal:
        out.append(f"- Average: {kcal:.0f} kcal")
    if protein:
        out.append(f"- Average protein: {protein:.0f} g")
    if len(rows) < days or incomplete:
        out.append("- ⚠ Averages cover logged days only; treat them as rough.")
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


def mark(ok):
    return "✓" if ok else "✗"


def targets_section(start, end):
    """Progress against private/profile/targets.json, week by week."""
    t = load_targets()
    if not t:
        return []
    out = ["## Targets", ""]

    # Weekly compliance: run miles, strength sessions, protein.
    runs = [r for r in read_csv(CARDIO_CSV) if r["type"].endswith("Run")]
    sets = read_csv(SETS_CSV)
    food = read_csv(NUTRITION_CSV)
    lo_mi, hi_mi = t.get("run_miles_per_week", (None, None))
    min_lift = t.get("strength_sessions_per_week_min")
    lo_p, hi_p = t.get("protein_g_per_day", (None, None))
    out += ["| Week | Run miles | Strength sessions | Avg protein (logged days) |", "|---|---|---|---|"]
    week_start = start - timedelta(days=start.weekday())
    while week_start <= end:
        week_end = week_start + timedelta(days=6)
        miles = sum(to_float(r["distance_km"]) or 0 for r in in_range(runs, week_start, week_end)) / KM_PER_MILE
        lifts = len({(r["date"], r["start_time"]) for r in in_range(sets, week_start, week_end)})
        prot = mean(to_float(r["protein_g"]) for r in in_range(food, week_start, week_end))
        partial = " (partial)" if week_end > end else ""
        cells = [f"{week_start.isoformat()}{partial}",
                 f"{miles:.1f} {mark(lo_mi <= miles <= hi_mi)}" if lo_mi is not None else f"{miles:.1f}",
                 f"{lifts} {mark(lifts >= min_lift)}" if min_lift else str(lifts),
                 (f"{prot:.0f} g {mark(lo_p <= prot)}" if lo_p else f"{prot:.0f} g") if prot else "—"]
        out.append("| " + " | ".join(cells) + " |")
        week_start += timedelta(days=7)
    out.append("")

    # Rate of weight loss on 7-day averages.
    weights = read_csv(WEIGHT_CSV)
    cur = mean(to_float(r["weight_kg"]) for r in in_range(weights, end - timedelta(days=6), end))
    prev = mean(to_float(r["weight_kg"]) for r in in_range(weights, end - timedelta(days=13), end - timedelta(days=7)))
    band = t.get("weekly_loss_pct_of_bodyweight")
    if cur and prev and band:
        loss_pct = (prev - cur) / prev * 100
        verdict = "on target" if band[0] <= loss_pct <= band[1] else ("too fast — muscle at risk" if loss_pct > band[1] else "slower than target")
        out.append(f"- Weight loss rate: {loss_pct:.2f}% of body weight/week (target {band[0]}–{band[1]}%) — {verdict}")

    # Body fat projection from the last DEXA, assuming fat-free mass is unchanged.
    dexa = [r for r in read_csv(BODY_COMP_CSV) if r.get("method") == "DEXA" and date.fromisoformat(r["date"]) <= end]
    goal_bf = t.get("body_fat_pct_dexa_max")
    if dexa and cur and goal_bf:
        d = dexa[-1]
        ffm = (to_float(d["lean_mass_kg"]) or 0) + (to_float(d["bone_mass_kg"]) or 0)
        est = (1 - ffm / cur) * 100
        goal_w = ffm / (1 - goal_bf / 100)
        out.append(f"- Body fat if lean mass held since DEXA {d['date']}: ~{est:.1f}% (goal < {goal_bf:g}%). "
                   f"Goal weight at that lean mass: {goal_w:.1f} kg ({cur - goal_w:.1f} kg to go). "
                   "Confirm with the next DEXA.")

    # Running fitness.
    goal_hm = t.get("half_marathon_minutes_max")
    found = best_effort(90, end)
    if goal_hm and found:
        vd, r = found
        out.append(f"- Running: best effort in 90 days ({r['date']}, {r['distance_km']} km) → VDOT ≈ {vd:.1f}, "
                   f"half marathon ≈ {fmt_time(race_time(vd, RACES['Half marathon']))}; "
                   f"target {fmt_time(goal_hm)} needs VDOT ≈ {vdot(RACES['Half marathon'], goal_hm):.1f}.")

    # Sleep.
    sleep_min = t.get("sleep_hours_min")
    sleep = mean(to_float(r["sleep_hours"]) for r in in_range(read_csv(MOOD_CSV), start, end))
    if sleep_min and sleep:
        out.append(f"- Sleep: {sleep:.1f} h average {mark(sleep >= sleep_min)} (target {sleep_min}+ h)")
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
    for section in (targets_section, weight_section, strength_section, cardio_section, nutrition_section,
                    mood_section):
        lines += section(start, end)
    report = "\n".join(lines)
    print(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
