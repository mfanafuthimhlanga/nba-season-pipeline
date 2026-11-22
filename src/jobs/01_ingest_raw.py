# Databricks notebook source
# MAGIC %md
# MAGIC # 01 ingest raw
# MAGIC Fetches one game date from ESPN and writes untouched JSON to the landing volume.
# MAGIC Job parameter `game_date`: blank = yesterday (US Eastern), or `YYYY-MM-DD`.
# MAGIC The resolved date is published as task value `game_date`, so the later
# MAGIC tasks load exactly this date even if the run crosses midnight in New York.

# COMMAND ----------

import os
import sys

# This notebook lives in src/jobs, so ".." is src, which contains the nba package.
sys.path.append(os.path.abspath(".."))

# COMMAND ----------

dbutils.widgets.text("game_date", "")

# COMMAND ----------

from nba import config, ingest

game_date = config.resolve_game_date(dbutils.widgets.get("game_date"))
dbutils.jobs.taskValues.set(key="game_date", value=game_date.isoformat())
ingest.run(game_date)