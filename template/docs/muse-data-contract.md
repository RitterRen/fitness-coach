# Muse data contract

Muse (the food/weight/mood logging assistant) writes to this repository.
This file is the agreement between Muse and the coach (Claude Code) on what
goes where. Muse may only change the four files listed below.

## General rules

- **English only.** Translate food names, tags and notes into English
  (e.g. 番茄炒蛋 → "tomato and egg stir-fry").
- **Dates:** `YYYY-MM-DD`, local time. **Times:** `HH:MM`, 24-hour.
- **CSV:** UTF-8, comma-separated, keep the header row exactly as it is,
  quote any field that contains a comma. No blank lines, no totals rows.
- **Units:** kg, kcal, grams. Leave a field empty if unknown — never guess.
- **Rows are sorted by date (then time)**, oldest first.
- **Commits:** one commit per upload, message `muse: <what> <first date>..<last date>`,
  e.g. `muse: meals, weight, mood 2026-10-01..2026-10-31`. Pull before pushing;
  never force-push; never touch other files.
- **Corrections:** to fix a past day, replace that day's rows; do not append duplicates.

## Files

### `data/nutrition/meals.csv` — one row per food item

| Column | Type | Notes |
|---|---|---|
| date | date | |
| time | HH:MM | empty if unknown |
| meal | text | `breakfast`, `lunch`, `dinner` or `snack` |
| food | text | English name |
| amount | number | |
| unit | text | `g`, `ml`, `piece`, `serving`, … |
| calories_kcal | number | |
| protein_g | number | |
| carbs_g | number | |
| fat_g | number | |
| note | text | optional |

### `data/nutrition/daily.csv` — one row per day (totals of meals.csv)

| Column | Type | Notes |
|---|---|---|
| date | date | unique |
| calories_kcal | number | |
| protein_g | number | |
| carbs_g | number | |
| fat_g | number | |
| note | text | optional, e.g. "eating out, estimate" |

### `data/body-weight.csv` — one row per day

| Column | Type | Notes |
|---|---|---|
| date | date | unique; if several weigh-ins, use the morning one |
| weight_kg | number | 1–2 decimals |
| body_fat_pct | number | optional |
| note | text | optional |
| source | text | `muse` (the local script writes `manual`) |

### `data/wellbeing/mood.csv` — one row per check-in

| Column | Type | Notes |
|---|---|---|
| date | date | |
| time | HH:MM | empty if unknown |
| mood_score | 1–5 | 1 = very low, 5 = very good |
| energy_score | 1–5 | 1 = exhausted, 5 = very energetic |
| stress_score | 1–5 | 1 = calm, 5 = very stressed |
| sleep_hours | number | previous night, optional |
| tags | text | semicolon-separated, e.g. `work;travel;sore legs` |
| note | text | short English summary of what was said |

Scores that were not recorded are left empty rather than estimated.
