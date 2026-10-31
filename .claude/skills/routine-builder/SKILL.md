---
name: routine-builder
description: Create or update a strength routine for a specific location and equipment set, in a format I can copy into the Xunji (训记) app. Use when I ask for a new routine, a gym/home/travel/outdoor workout, an exercise swap, or progression changes.
---
# Routine builder

1. Read `private/profile/athlete.md` (locations and equipment), `private/profile/medical-history.md` (restrictions), `private/profile/goals.md` and `targets.json` (sessions per week, running volume), `private/plan/program.md`, and the last 28 days of `private/data/strength/sets.csv` for current working loads.
2. If the routine is for a specific day, check Google Calendar (if connected) for where I will be and how long I have.
3. Write or update `private/plan/routines/<location>-<name>.md` using the template in `private/plan/routines/README.md`:
   - English name plus the Chinese name Xunji shows (so the importer and I can match them)
   - Warm-up ramp sets for the first compound lift
   - Sets × reps, load in kg, target RPE, rest time for every exercise
   - A substitution for any exercise that needs equipment that is often taken
4. At the top, under **Changes**, list every difference from the previous version — this is my checklist for editing the template in Xunji, because Claude cannot push to the app.
5. While in a calorie deficit, keep intensity high (working sets at RPE 7–9) and volume moderate (about 10–16 hard sets per muscle per week); drop volume before load. Schedule heavy lower-body work away from the long run and the quality run (not the day before), and keep at least one full rest day.
6. Briefly justify non-obvious choices (exercise selection, volume, progression) with the evidence behind them.
7. Commit in `private/` (`git -C private commit`, then push): `routine: <file> <short summary>`.
