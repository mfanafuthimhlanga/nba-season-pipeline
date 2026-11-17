# Databricks notebook source
# MAGIC %md
# MAGIC # 01 ingest raw
# MAGIC Fetches one game date from ESPN and writes untouched JSON to the landing volume.
# MAGIC Job parameter `game_date`: blank = yesterday (US Eastern), or `YYYY-MM-DD`.

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
ingest.run(game_date)