-- Heartbeat for the nba_daily job (issue #38).
--
-- Every run of nba_daily adds a row to nba.bronze.scoreboard, games or not,
-- so the newest ingested_at is the time of the last run. This query returns
-- the hours since then: one row, one number.
--
-- It runs as a Databricks SQL alert, outside the job, so it still fires
-- when the job never starts (a paused schedule, a stuck queue):
--   saved query  nba heartbeat
--   alert        nba_daily did not run
--   condition    hours_since_load > 12
--   schedule     daily at 12:00 UTC, on the SQL warehouse
--   notify       on trigger and when back to OK
-- A run lands at about 09:01 UTC, so at 12:00 a healthy value is about 3
-- and a missed run about 27. The alert lives in the Databricks UI; this file
-- is its copy for review. Change both together.
select timestampdiff(HOUR, max(ingested_at), current_timestamp()) as hours_since_load
from nba.bronze.scoreboard
