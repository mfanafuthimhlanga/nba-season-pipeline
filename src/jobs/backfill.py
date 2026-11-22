# Databricks notebook source
# MAGIC %md
# MAGIC # Backfill
# MAGIC Runs ingest -> bronze -> silver for every date in a range, using the SAME
# MAGIC functions as the daily job. dbt is not run here: run it once afterwards.
# MAGIC
# MAGIC Widgets:
# MAGIC - `start_date`: first date, blank = the season start (config.SEASON_START)
# MAGIC - `end_date`: last date, blank = yesterday (US Eastern)
# MAGIC
# MAGIC A failed date does not stop the loop. Failures are listed at the end, and
# MAGIC then the notebook raises, so a run with any failed date ends red (and a
# MAGIC job's failure email fires). Rerun just those dates by setting both widgets
# MAGIC to the same date.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath(".."))

# COMMAND ----------

dbutils.widgets.text("start_date", "")
dbutils.widgets.text("end_date", "")

# COMMAND ----------

import time
import traceback
from datetime import timedelta

from nba import bronze, config, ingest, silver

start = config.resolve_game_date(dbutils.widgets.get("start_date") or config.SEASON_START.isoformat())
end = config.resolve_game_date(dbutils.widgets.get("end_date"))
if start > end:
    raise ValueError(f"start_date {start} is after end_date {end}")

dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
print(f"Backfilling {len(dates)} dates: {start} to {end}")

# COMMAND ----------

results = []   # one dict per successful date
failures = []  # (date, step, error message)

for d in dates:
    t0 = time.time()
    step = "ingest"
    try:
        ingest.run(d)
        step = "bronze"
        bronze.run(d)
        step = "silver"
        s = silver.run(d)
        results.append({**s, "seconds": round(time.time() - t0, 1)})
    except Exception as e:
        failures.append((d.isoformat(), step, f"{type(e).__name__}: {e}"))
        print(f"FAILED {d} at {step}: {type(e).__name__}: {e}")
        traceback.print_exc()

# COMMAND ----------

total_games = sum(r["games"] for r in results)
print(f"Succeeded: {len(results)} dates, {total_games} games")
print(f"Failed:    {len(failures)} dates")
for f in failures:
    print("  ", f)

if results:
    display(spark.createDataFrame(results))

if failures:
    raise RuntimeError(f"{len(failures)} of {len(dates)} dates failed: {[f[0] for f in failures]}")