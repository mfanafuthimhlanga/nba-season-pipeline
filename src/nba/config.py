"""Single source of truth for names, paths, source settings and date rules."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# --- Unity Catalog -----------------------------------------------------------
# Every Python job reads these names. The catalog name "nba" is also written in
# three places Python cannot reach; change them together:
#   src/setup/00_setup.sql        (catalog, schemas, volume, silver tables)
#   dbt/nba/models/_sources.yml   (source database)
#   ~/.dbt/profiles.yml / the job's dbt task  (catalog)
# If CREATE CATALOG is refused (Databricks Free Edition), use CATALOG =
# "workspace" and change the same three places.
CATALOG = "nba"
BRONZE = f"{CATALOG}.bronze"
SILVER = f"{CATALOG}.silver"

# --- Raw landing zone (UC volume) --------------------------------------------
VOLUME_ROOT = f"/Volumes/{CATALOG}/raw/landing"
SCOREBOARD_DIR = f"{VOLUME_ROOT}/scoreboard"
SUMMARY_DIR = f"{VOLUME_ROOT}/summary"
SCOREBOARD_FILE = "scoreboard.json"  # written LAST: its presence marks a complete date

# --- Source: ESPN (unofficial, undocumented) ----------------------------------
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
REQUEST_TIMEOUT_S = 15
REQUEST_PAUSE_S = 0.5   # be polite between calls
MAX_ATTEMPTS = 3        # for connection errors, 429 and 5xx only
MAX_RETRY_AFTER_S = 60  # cap on a 429's Retry-After header

# --- Season and status rules --------------------------------------------------
SEASON_START = date(2026, 10, 20)  # also var season_start in dbt/nba/dbt_project.yml
GAME_DAY_TZ = ZoneInfo("America/New_York")  # ESPN "dates" = US Eastern game day
FINAL_STATUS = "STATUS_FINAL"
SKIP_STATUSES = frozenset({"STATUS_POSTPONED", "STATUS_CANCELED"})


def resolve_game_date(value: str | None) -> date:
    """Blank or None -> yesterday's US Eastern date. Otherwise parse YYYY-MM-DD.

    Raises ValueError on a malformed date, so a bad job parameter fails loudly.
    """
    value = (value or "").strip()
    if not value:
        return (datetime.now(GAME_DAY_TZ) - timedelta(days=1)).date()
    return date.fromisoformat(value)


def date_partition(game_date: date) -> str:
    """Folder name for one game date, e.g. 'game_date=2026-11-15'."""
    return f"game_date={game_date.isoformat()}"
