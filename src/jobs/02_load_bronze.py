# Databricks notebook source
# MAGIC %md
# MAGIC # 02 load bronze
# MAGIC Loads one game date's raw JSON files into the bronze Delta tables.
# MAGIC Job parameter `game_date`: blank = the date the ingest_raw task resolved in
# MAGIC this run (or yesterday, US Eastern, when run on its own), or `YYYY-MM-DD`.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath(".."))

# COMMAND ----------

dbutils.widgets.text("game_date", "")

# COMMAND ----------

from nba import bronze, config

# Same date as ingest_raw in this run. Outside a job run, debugValue "" -> yesterday.
from_ingest = dbutils.jobs.taskValues.get(taskKey="ingest_raw", key="game_date", default="", debugValue="")
game_date = config.resolve_game_date(dbutils.widgets.get("game_date") or from_ingest)
bronze.run(game_date)