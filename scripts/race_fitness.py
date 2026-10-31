#!/usr/bin/env python3
"""Running fitness from Strava runs: VDOT, race predictions and training paces.

Uses Jack Daniels' VDOT formulas. A training run only gives a lower bound on
fitness (it was not run all-out), so the estimate comes from the best recent
effort; a real race or time trial is far more accurate.

    python3 scripts/race_fitness.py                    # best effort of the last 90 days
    python3 scripts/race_fitness.py --days 180
    python3 scripts/race_fitness.py --race 21.0975 1:57:18   # VDOT for a known result
"""

import argparse
import json
import math
from datetime import date, timedelta

from common import CARDIO_CSV, TARGETS_JSON, read_csv, require_private, to_float

KM_PER_MILE = 1.609344
RACES = {"5K": 5000, "10K": 10000, "Half marathon": 21097.5, "Marathon": 42195}
# Fraction of VDOT (VO2) for each training pace — approximations of Daniels' tables.
PACES = {"Easy": (0.62, 0.70), "Marathon": (0.80, 0.80), "Threshold": (0.88, 0.88), "Interval": (0.975, 0.975)}
MIN_RUN_KM = 5.0


def vo2_at(v):
    """Oxygen cost (ml/kg/min) of running at v metres per minute."""
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def pct_max(t):
    """Fraction of VO2max sustainable for t minutes."""
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t) + 0.2989558 * math.exp(-0.1932605 * t)


def vdot(distance_m, minutes):
    return vo2_at(distance_m / minutes) / pct_max(minutes)


def race_time(vd, distance_m):
    """Minutes to run distance_m at a given VDOT (bisection)."""
    lo, hi = 1.0, 600.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if vdot(distance_m, mid) > vd else (lo, mid)
    return (lo + hi) / 2


def speed_for_vo2(target):
    """Metres per minute that costs `target` ml/kg/min (inverse of vo2_at)."""
    a, b, c = 0.000104, 0.182258, -4.60 - target
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def fmt_time(minutes):
    s = round(minutes * 60)
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_pace(m_per_min, per_m):
    return fmt_time(per_m / m_per_min)


def parse_time(text):
    parts = [float(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 60 + m + s / 60


def best_effort(days, end=None):
    """Best VDOT among runs of at least MIN_RUN_KM in the window, or None."""
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    best = None
    for r in read_csv(CARDIO_CSV):
        if not r["type"].endswith("Run") or not (start <= date.fromisoformat(r["date"]) <= end):
            continue
        km, mins = to_float(r["distance_km"]), to_float(r["moving_min"])
        if not km or not mins or km < MIN_RUN_KM:
            continue
        v = vdot(km * 1000, mins)
        if best is None or v > best[0]:
            best = (v, r)
    return best


def load_targets():
    return json.loads(TARGETS_JSON.read_text(encoding="utf-8")) if TARGETS_JSON.exists() else {}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--race", nargs=2, metavar=("KM", "TIME"), help="e.g. --race 21.0975 1:57:18")
    args = p.parse_args()

    if args.race:
        km, mins = float(args.race[0]), parse_time(args.race[1])
        vd, source = vdot(km * 1000, mins), f"{km:g} km in {fmt_time(mins)}"
    else:
        require_private()
        found = best_effort(args.days)
        if not found:
            print(f"No runs of {MIN_RUN_KM:g} km+ in the last {args.days} days.")
            return
        vd, r = found
        source = f"{r['date']} {r['name']} — {r['distance_km']} km in {fmt_time(float(r['moving_min']))} (Strava moving time)"

    print(f"VDOT ≈ {vd:.1f}  from {source}\n")
    print("Equivalent race times:")
    for name, d in RACES.items():
        print(f"  {name:<14} {fmt_time(race_time(vd, d))}")

    print("\nTraining paces (per km / per mile):")
    for name, (lo, hi) in PACES.items():
        fast, slow = speed_for_vo2(hi * vd), speed_for_vo2(lo * vd)
        km_p = fmt_pace(fast, 1000) if lo == hi else f"{fmt_pace(fast, 1000)}–{fmt_pace(slow, 1000)}"
        mi_p = fmt_pace(fast, KM_PER_MILE * 1000) if lo == hi else \
            f"{fmt_pace(fast, KM_PER_MILE * 1000)}–{fmt_pace(slow, KM_PER_MILE * 1000)}"
        print(f"  {name:<10} {km_p:>13} /km   {mi_p:>13} /mi")

    target = load_targets().get("half_marathon_minutes_max")
    if target:
        needed = vdot(RACES["Half marathon"], target)
        print(f"\nHalf-marathon target {fmt_time(target)} needs VDOT ≈ {needed:.1f} "
              f"({needed - vd:+.1f} from now).")


if __name__ == "__main__":
    main()
