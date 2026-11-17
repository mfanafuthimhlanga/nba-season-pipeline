# Databricks notebook source
# MAGIC %md
# MAGIC # 02 load bronze
# MAGIC Loads one game date's raw JSON files into the bronze Delta tables.
# MAGIC Job parameter `game_date`: blank = yesterday (US Eastern), or `YYYY-MM-DD`.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath(".."))

# COMMAND ----------

dbutils.widgets.text("game_date", "")

# COMMAND ----------

from nba import bronze, config

game_date = config.resolve_game_date(dbutils.widgets.get("game_date"))
bronze.run(game_date)