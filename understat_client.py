import soccerdata as sd
import pandas as pd
from rapidfuzz import process, fuzz


def _fuzzy_match_col(name: str, candidates: pd.Series, threshold: int = 80) -> str | None:
    result = process.extractOne(name, candidates, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0]
    return None

# Understat league names mapped from our internal league IDs
UNDERSTAT_LEAGUE_MAP = {
    39:  "ENG-Premier League",
    140: "ESP-La Liga",
    78:  "GER-Bundesliga",
    135: "ITA-Serie A",
    61:  "FRA-Ligue 1",
}

CURRENT_SEASON  = "2627"
FALLBACK_SEASON = "2526"

_DEFAULTS = {"xg_for": 1.35, "xg_against": 1.15}


class UnderstatClient:
    """
    Pulls per-match xG data from Understat via soccerdata.
    Caches schedule per league — only scrapes once per league per session.
    Priority: Understat > FBref season xG > hardcoded defaults.
    """

    def __init__(self):
        self._cache: dict = {}  # league_id -> schedule DataFrame

    def _get_schedule(self, league_id: int) -> pd.DataFrame | None:
        if league_id in self._cache:
            return self._cache[league_id]

        league_name = UNDERSTAT_LEAGUE_MAP.get(league_id)
        if not league_name:
            return None

        try:
            try:
                us = sd.Understat(leagues=league_name, seasons=CURRENT_SEASON)
                df = us.read_schedule()
                df = df.reset_index()
                if df.empty or "home_team" not in df.columns:
                    raise ValueError("empty or missing columns")
            except Exception:
                print(f"[Understat] {CURRENT_SEASON} unavailable for {league_name} - falling back to {FALLBACK_SEASON}")
                us = sd.Understat(leagues=league_name, seasons=FALLBACK_SEASON)
                df = us.read_schedule()
                df = df.reset_index()
            self._cache[league_id] = df
            return df
        except Exception as e:
            print(f"[Understat] Failed to fetch {league_name}: {e}")
            return None

    def get_team_xg_stats(self, team_name: str, league_id: int, fbref_stats: dict | None = None) -> dict:
        """Returns avg xg_for and xg_against per game. Falls back to FBref xG then hardcoded defaults."""
        df = self._get_schedule(league_id)

        if df is not None:
            home = df[df["home_team"] == team_name]
            away = df[df["away_team"] == team_name]

            if home.empty and away.empty:
                home = df[df["home_team"].str.contains(team_name, case=False, na=False)]
                away = df[df["away_team"].str.contains(team_name, case=False, na=False)]

            if home.empty and away.empty:
                all_teams = pd.concat([df["home_team"], df["away_team"]]).unique()
                match = _fuzzy_match_col(team_name, pd.Series(all_teams))
                if match:
                    home = df[df["home_team"] == match]
                    away = df[df["away_team"] == match]

            total_games = len(home) + len(away)
            if total_games > 0:
                xg_for     = home["home_xg"].astype(float).sum() + away["away_xg"].astype(float).sum()
                xg_against = home["away_xg"].astype(float).sum() + away["home_xg"].astype(float).sum()
                return {
                    "xg_for":     round(xg_for / total_games, 2),
                    "xg_against": round(xg_against / total_games, 2),
                }

        # Understat unavailable or no matches yet — try FBref xG
        if fbref_stats:
            fbref_xg_for     = fbref_stats.get("xg_for")
            fbref_xg_against = fbref_stats.get("xg_against")
            if fbref_xg_for is not None and fbref_xg_against is not None:
                print(f"[Understat] Using FBref xG fallback for {team_name}")
                return {"xg_for": fbref_xg_for, "xg_against": fbref_xg_against}

        print(f"[Understat] Using hardcoded defaults for {team_name}")
        return _DEFAULTS.copy()
