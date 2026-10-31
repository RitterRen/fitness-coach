---
name: goal-check
description: Check progress against my goals (body fat via DEXA, race target, weekly strength sessions, weekly running miles, rate of weight loss, protein, sleep) and say whether the goals and timeline are still realistic. Use when I ask "am I on track", "are my goals realistic", about my goals, body fat target, race goal, or after a new DEXA scan.
---
# Goal check

Goals live in `private/profile/goals.md` (the reasoning and phases) and
`private/profile/targets.json` (the numbers the scripts check). Keep them in sync.

1. `git -C private pull`, then gather the numbers:
   - `python3 scripts/weekly_report.py --days 28` — the **Targets** section gives week-by-week run miles, strength sessions and protein, the weight-loss rate, projected body fat from the last DEXA, VDOT and sleep.
   - `python3 scripts/race_fitness.py --days 90` — current VDOT, predicted race times and training paces. If I give an official race result, use `--race <km> <h:mm:ss>` instead; Strava GPS distance and moving time flatter the result.
   - `private/data/body-composition.csv` — DEXA history. Only DEXA counts for the body-fat goal; BIA/smart-scale rows are trend hints only.
2. Assess each goal:
   - **Body fat:** fat mass to lose = current fat mass − (fat-free mass ÷ (1 − target%)) × target%. Divide by a sustainable 0.5–1.0% of body weight per week to get a date range. If lean mass dropped by more than ~1 kg between DEXAs, the deficit or protein is wrong — say so first.
   - **Race:** compare current VDOT with the VDOT the target needs. Credit expected weight loss (VDOT scales roughly with 1/body mass if absolute fitness holds) and consistent training (typically +2–4 VDOT over 6–12 months for a recreational runner). Recommend a race date that fits.
   - **Training volume:** weeks meeting the strength-session minimum and the mileage range; flag spikes (>10–15% jumps in weekly miles) and gaps.
   - **Supporting targets:** loss rate, protein, calories, sleep.
3. Reply with: a one-line verdict per goal (on track / at risk / unrealistic), the numbers behind it, and at most three changes for the next 2–4 weeks. Be honest when a goal or date needs to move.
4. If targets or phases change, update `goals.md` and `targets.json`, then commit in `private/` (`git -C private commit`, then push): `goals: <short summary>`.
