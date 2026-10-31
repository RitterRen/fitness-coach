---
name: session-review
description: Review a training session I just finished (strength from Xunji or a run from Strava/Apple Watch), compare it with the prescription, write the review file and set next time's targets. Use when I say I finished a workout, a run, intervals, or want feedback on today's training.
argument-hint: [how it felt, anything that was off]
---
# Session review

My notes: $ARGUMENTS

1. **Pull fresh data.**
   - `git -C private pull` for the latest Muse data (food, weight, mood).
   - If `private/inbox/xunji/` has files, run `python3 scripts/import_xunji.py` (see the `xunji-import` skill if it fails).
   - Run `python3 scripts/strava_sync.py` unless `.env` has no Strava keys.
2. **Find today's session** in `private/data/strength/sets.csv` and/or `private/data/cardio/activities.csv`. Compare it with the routine in `private/plan/routines/` and with the previous time I did the same routine or workout.
3. **Runs:** check pace against the training paces from `python3 scripts/race_fitness.py` — most runs should be in the Easy range; say so when an "easy" run was really marathon pace or faster. When splits or HR drift matter (intervals, tempo, long run), fetch per-second data with `python3 scripts/strava_sync.py --streams <strava_id>` and analyse rep-by-rep pace and HR recovery.
4. **Write** `private/reviews/sessions/<date>-<type>.md`:
   - Done vs prescribed (table)
   - What I reported
   - What the data says
   - Targets for next time: loads, warm-up ramp, exercise swaps — or the next run workout, written so I can enter it on Apple Watch (intervals, paces, HR zones)
5. **Routine changes:** if needed, use the `routine-builder` skill to edit the routine and tell me exactly what to change in Xunji.
6. Commit in `private/` (`git -C private commit`, then push): `review: <date> <type>`.

Keep the reply short: three to six bullet points plus the next target.
