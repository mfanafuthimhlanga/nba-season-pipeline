# Databricks notebook source
# MAGIC %md
# MAGIC # 03 build silver
# MAGIC Parses one game date's bronze payloads and MERGEs into the silver tables.
# MAGIC Job parameter `game_date`: blank = yesterday (US Eastern), or `YYYY-MM-DD`.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath(".."))

# COMMAND ----------

dbutils.widgets.text("game_date", "")

# COMMAND ----------

from nba import config, silver

game_date = config.resolve_game_date(dbutils.widgets.get("game_date"))
silver.run(game_date)