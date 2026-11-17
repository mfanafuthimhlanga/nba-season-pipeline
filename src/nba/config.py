"""Single source of truth for names, paths, source settings and date rules."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# --- Unity Catalog -----------------------------------------------------------
# If CREATE CATALOG was refused on Free Edition, change CATALOG to "workspace"
# and prefix the schema names (e.g. "nba_bronze"). Nothing else needs to change.
CATALOG = "nba"
BRONZE = f"{CATALOG}.bronze"
SILVER = f"{CATALOG}.silver"

# --- Raw landing zone (UC volume) --------------------------------------------
VOLUME_ROOT = f"/Volumes/{CATALOG}/raw/landing"
SCOREBOARD_DIR = f"{VOLUME_ROOT}/scoreboard"
SUMMARY_DIR = f"{VOLUME_ROOT}/summary"

# --- Source: ESPN (unofficial, undocumented) ----------------------------------
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
REQUEST_TIMEOUT_S = 15
REQUEST_PAUSE_S = 0.5   # be polite between calls
MAX_ATTEMPTS = 3        # for connection errors and 5xx only

# --- Season and status rules --------------------------------------------------
SEASON_START = date(2026, 10, 20)
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