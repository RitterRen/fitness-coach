# Muse data contract

Muse (the food/weight/mood logging assistant) writes to this repository.
This file is the agreement between Muse and the coach (Claude Code) on what
goes where. Muse may only change the four files listed below.

**Version 2** — estimates are allowed for nutrition (and required for the
daily totals), and mood is captured with a daily 1–5 check-in.

## General rules

- **English only.** Translate food names, tags and notes into English
  (e.g. 番茄炒蛋 → "tomato and egg stir-fry"). Write notes in the first
  person, as the athlete would ("felt tired after work").
- **Dates:** `YYYY-MM-DD`, local time. **Times:** `HH:MM`, 24-hour.
- **CSV:** UTF-8, comma-separated, keep the header row exactly as it is,
  quote any field that contains a comma. No blank lines, no totals rows.
- **Units:** kg, kcal, grams.
- **Rows are sorted by date (then time)**, oldest first.
- **Commits:** one commit per upload, message `muse: <what> <first date>..<last date>`
  for backfills and `muse: <YYYY-MM-DD>` for the daily push. Pull before
  pushing; never force-push; never touch other files.
- **Corrections:** to fix a past day, replace that day's rows; do not append
  duplicates. A daily push may also correct earlier days.

## Estimates vs. invented data

The coach needs a number every day more than it needs a perfect number.

- **Nutrition values may be estimated.** If the log gives a range, use the
  midpoint, rounded (kcal to the nearest 10, grams to the nearest 1). If it
  gives nothing, estimate from typical portions. Every estimated row gets
  `estimate` at the start of its `note` (e.g. `estimate; log range 600-1000 kcal`).
- **Never invent events.** Do not add meals that were not eaten, weigh-ins
  that did not happen, or mood scores the athlete did not give. Leave those
  empty or leave the row out.
- **Never infer mood scores from text.** Scores come only from the athlete's
  own rating in the daily check-in.

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
| calories_kcal | number | estimate allowed |
| protein_g | number | estimate allowed |
| carbs_g | number | estimate allowed, optional |
| fat_g | number | estimate allowed, optional |
| note | text | starts with `estimate` if any number is estimated |

When a log gives one estimate for a group of items, put the numbers on the
first item of the group and say so in the note of the others
(`included in <first item>`).

### `data/nutrition/daily.csv` — one row per day, **required**

Write a row for **every day that has any food logged**, including days with
only drinks or a single meal.

| Column | Type | Notes |
|---|---|---|
| date | date | unique |
| calories_kcal | number | **required** — everything eaten and drunk that day, estimate if needed |
| protein_g | number | **required** — estimate if needed |
| carbs_g | number | optional |
| fat_g | number | optional |
| note | text | `estimate` first if estimated; say if the day is incomplete (e.g. `incomplete: dinner not logged`) |

The daily total should match the sum of that day's `meals.csv` rows. If the
log's own day total disagrees, use the one that includes every item (drinks
and snacks too) and mention the other in the note.

### `data/body-weight.csv` — one row per day

| Column | Type | Notes |
|---|---|---|
| date | date | unique; if several weigh-ins, use the morning one |
| weight_kg | number | 1–2 decimals |
| body_fat_pct | number | from a DEXA scan or smart scale, when measured |
| note | text | e.g. `morning fasting`, `DEXA scan` |
| source | text | `muse` (the local script writes `manual`) |

DEXA or other body-composition scans: add `body_fat_pct` and `DEXA scan` in
the note. If there is no scale weigh-in that day, use the scan's weight.

### `data/wellbeing/mood.csv` — one row per check-in

Muse asks for a **daily check-in** once a day, in the evening:

> Mood, energy, stress — 1 to 5 each? How many hours did you sleep last night?

| Column | Type | Notes |
|---|---|---|
| date | date | |
| time | HH:MM | time of the check-in |
| mood_score | 1–5 | 1 = very low, 5 = very good |
| energy_score | 1–5 | 1 = exhausted, 5 = very energetic |
| stress_score | 1–5 | 1 = calm, 5 = very stressed |
| sleep_hours | number | previous night |
| tags | text | semicolon-separated, e.g. `work;travel;sore legs` |
| note | text | short first-person summary of anything said about how the day felt |

If the check-in is skipped, still add a row when there are notes or sleep
data, with the scores left empty.
