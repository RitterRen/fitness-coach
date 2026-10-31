---
name: log-weight
description: Log a body-weight reading and report the 7-day average trend. Use when I mention a weigh-in, my weight today, or ask how my weight is trending.
argument-hint: <weight-kg> [note]
---
# Log weight

1. Run `python3 scripts/log_weight.py <kg>` from the repo root. If a note follows the number, pass it with `--note "<note>"`. If I give a past date, add `--date YYYY-MM-DD`. If I only ask about the trend, use `--show`.
2. Comment in one or two sentences on the 7-day average change against the target rate in `private/profile/goals.md`. Never react to a single weigh-in; daily swings of ±1 kg are water and glycogen.
3. Commit in `private/` (`git -C private commit`, then push): `weight: <date> <kg>`.

Arguments: $ARGUMENTS
