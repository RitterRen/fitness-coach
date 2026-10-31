---
name: weekly-review
description: Weekly training review across weight, strength, running and nutrition, then plan next week around my calendar. Use at the end of a week or when I ask how the week went or what next week should look like.
---
# Weekly review

1. `git -C private pull` (Muse data), then pull fresh Xunji and Strava data as in `session-review`.
2. Run `python3 scripts/weekly_report.py --days 7` and `python3 scripts/weekly_report.py --days 28` (the 28-day training ledger). Start the review from the **Targets** section: it checks the week against `private/profile/targets.json`.
3. If Google Calendar is connected, read next week's events: where I will be, and which windows are free and long enough.
4. Write `private/reviews/weekly/<YYYY>-W<ww>.md`:
   - Weight: 7-day average trend vs the goal rate
   - Strength: progress on each main lift (top set, e1RM), weekly sets per muscle group
   - Running: volume, longest run, easy/hard split, any HR or pace trend
   - Nutrition: average calories and protein vs target, days logged
   - Mood, energy, stress and sleep from `private/data/wellbeing/mood.csv`, and how they line up with training load
   - Recovery and anything from my notes or `private/profile/medical-history.md` to watch
   - Goals: one line each from the Targets section (on track / at risk), and whether `goal-check` should be run (every 4 weeks or after a DEXA)
   - Decisions for next week
5. Update `private/plan/program.md` (current week, next week's day-by-day schedule matched to location and free time, meeting the strength-session minimum and the weekly mileage range in targets.json, with at least one full rest day) and use `routine-builder` for any routine edits.
6. Commit in `private/` (`git -C private commit`, then push): `review: <YYYY>-W<ww>`.
