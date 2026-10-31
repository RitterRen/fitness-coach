---
name: body-comp-import
description: Import a body-composition report (DEXA such as BodySpec, or a smart-scale/BIA report such as RENPHO) from iCloud Drive or a file I point to, store it in the private repo and add a row to body-composition.csv. Use when I mention a new DEXA scan, body-fat report, InBody/RENPHO report, or ask to fetch a scan from iCloud.
---
# Body-composition import

1. **Find the file.** iCloud Drive is at `~/Library/Mobile Documents/com~apple~CloudDocs/`.
   Search it (and `~/Downloads`, `~/Documents`, `~/Desktop`) for names containing
   DEXA, DXA, BodySpec, InBody, RENPHO, body composition, 体脂, 体成分 or 骨密度,
   and match the scan date I gave. If several match, ask which one.
2. **Copy** it to `private/records/body-composition/<YYYY-MM-DD>-<provider>-<dexa|bia>.pdf`.
   Never put these files in the public repo.
3. **Read it.** Try `pdftotext -layout <file> -`; if the PDF is image-only, render
   pages with `pdftoppm -r 80 -png` and read the images. (Install with
   `brew install poppler` if missing.)
4. **Append a row** to `private/data/body-composition.csv` (keep the header and
   column order; convert lb to kg with 0.45359237; one decimal for %, two for kg):
   `date, method (DEXA|BIA), provider, weight_kg, body_fat_pct, fat_mass_kg,
   lean_mass_kg (excluding bone), bone_mass_kg, visceral_fat (with unit, or "index N"),
   lean_mass_index_kg_m2, almi_kg_m2, bone_density_g_cm2, rmr_kcal, note, file`.
   Put percentiles, regional values and anything else useful in `note`.
5. **Compare** with the previous scan of the **same method**: change in weight,
   fat mass, lean mass, body fat %. Never compare BIA body fat with DEXA body fat
   — BIA usually reads several points lower.
6. If it is a DEXA, run the `goal-check` skill afterwards.
7. Commit in `private/` (`git -C private commit`, then push): `data: <method> <date>`.
