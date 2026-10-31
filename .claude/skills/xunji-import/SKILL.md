---
name: xunji-import
description: Import strength-training exports from the Xunji (训记) app into private/data/strength/sets.csv, and fix the importer when Xunji's export columns are not recognised. Use when I say I exported from Xunji, dropped a file in the inbox, or the import fails.
---
# Xunji import

Xunji has no public API, so data arrives as export files in `private/inbox/xunji/` (.csv or .xlsx).

1. Preview: `python3 scripts/import_xunji.py --dry-run`. Check the dates, exercise names, kg and reps look right (watch for lb vs kg, and warm-up sets).
2. Import: `python3 scripts/import_xunji.py`. Re-importing overlapping exports is safe; rows are deduplicated on date, time, exercise, set, weight and reps.
3. **If it stops with unrecognised columns:** show me the header row it printed, then add the Chinese header names to `COLUMN_ALIASES` in `scripts/import_xunji.py` under the right field. If the layout is something new (e.g. one row per workout), extend `parse_file` and add a test file under `scripts/samples/`. Do not guess what a column means; ask me.
4. Leave the raw export in `private/inbox/xunji/` (it is the history) and commit both in `private/`: `data: import xunji <date range>`.
