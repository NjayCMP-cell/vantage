import soccerdata as sd
import pandas as pd
from rapidfuzz import process, fuzz


def _fuzzy_match(name: str, candidates: pd.Series, threshold: int = 80) -> str | None:
    """Returns best fuzzy match from candidates above threshold, or None."""
    result = process.extractOne(name, candidates, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0]
    return None

# FBref league codes mapped to our internal league IDs
LEAGUE_MAP = {
    39:  "ENG-Premier League",
    140: "ESP-La Liga",
    78:  "GER-Bundesliga",
    135: "ITA-Serie A",
    61:  "FRA-Ligue 1",
    # POR-Primeira Liga and NED-Eredivisie not supported by FBref soccerdata
}

CURRENT_SEASON  = "2627"
FALLBACK_SEASON = "2526"


class FBrefClient:
    """
    Pulls current season team stats from FBref via soccerdata.
    Caches data per league — only scrapes once per league per session.
    """

    def __init__(self):
        self._cache: dict = {}         # league_id -> merged season stats DataFrame
        self._schedule_cache: dict = {} # league_id -> match schedule DataFrame

    def _get_league_stats(self, league_id: int) -> pd.DataFrame | None:
        """Fetch and merge all stat types for a league. Cached after first call."""
        if league_id in self._cache:
            return self._cache[league_id]

        league_name = LEAGUE_MAP.get(league_id)
        if not league_name:
            return None

        def _fetch(season: str):
            fbref = sd.FBref(leagues=league_name, seasons=season)
            standard = fbref.read_team_season_stats(stat_type="standard")
            shooting = fbref.read_team_season_stats(stat_type="shooting")
            keeper   = fbref.read_team_season_stats(stat_type="keeper")
            misc     = fbref.read_team_season_stats(stat_type="misc")
            return standard, shooting, keeper, misc

        try:
            try:
                standard, shooting, keeper, misc = _fetch(CURRENT_SEASON)
                if standard.empty:
                    raise ValueError("empty")
            except Exception:
                print(f"[FBref] {CURRENT_SEASON} unavailable for {league_name} - falling back to {FALLBACK_SEASON}")
                standard, shooting, keeper, misc = _fetch(FALLBACK_SEASON)

            for df in [standard, shooting, keeper, misc]:
                df.columns = ["_".join(c).strip("_") for c in df.columns]

            standard = standard.reset_index()
            shooting = shooting.reset_index()
            keeper   = keeper.reset_index()
            misc     = misc.reset_index()

            merged = standard.merge(shooting, on=["league", "season", "team"], suffixes=("", "_sh"))
            merged = merged.merge(keeper,     on=["league", "season", "team"], suffixes=("", "_k"))
            merged = merged.merge(misc,       on=["league", "season", "team"], suffixes=("", "_m"))
            merged["games_played"] = merged.get("Playing Time_MP", pd.Series([1] * len(merged)))

            self._cache[league_id] = merged
            return merged

        except Exception as e:
            print(f"[FBref] Failed to fetch {league_name}: {e}")
            return None

    def _get_schedule(self, league_id: int) -> pd.DataFrame | None:
        """Fetch match schedule stats (Poss, Formation) for a league. Cached after first call."""
        if league_id in self._schedule_cache:
            return self._schedule_cache[league_id]

        league_name = LEAGUE_MAP.get(league_id)
        if not league_name:
            return None

        try:
            fbref = sd.FBref(leagues=league_name, seasons=CURRENT_SEASON)
            df = fbref.read_team_match_stats(stat_type="schedule")
            df = df.reset_index()
            self._schedule_cache[league_id] = df
            return df
        except Exception as e:
            print(f"[FBref] Failed to fetch schedule for {league_name}: {e}")
            return None

    def get_possession_and_formation(self, team_name: str, league_id: int) -> dict:
        """Returns average possession % and most-used formation for a team."""
        df = self._get_schedule(league_id)
        if df is None:
            return {"possession": 50.0, "formation": "4-3-3"}

        team_df = df[df["team"].str.lower() == team_name.lower()]
        if team_df.empty:
            team_df = df[df["team"].str.lower().str.contains(team_name.lower(), na=False)]
        if team_df.empty:
            match = _fuzzy_match(team_name, df["team"])
            if match:
                team_df = df[df["team"] == match]
        if team_df.empty:
            return {"possession": 50.0, "formation": "4-3-3"}

        avg_poss = team_df["Poss"].astype(float).mean()
        f_mode = team_df["Formation"].mode()
        top_formation = str(f_mode.iloc[0]) if not f_mode.empty else "4-3-3"

        return {
            "possession": round(float(avg_poss), 1),
            "formation": top_formation,
        }

    def get_team_stats(self, team_name: str, league_id: int) -> dict | None:
        """
        Returns per-game averages for a team:
        goals_for, goals_against, sot_for, sot_against, saves, cards, crosses
        """
        df = self._get_league_stats(league_id)
        if df is None:
            return None

        # Find team row — exact, partial, then fuzzy
        row = df[df["team"].str.lower() == team_name.lower()]
        if row.empty:
            row = df[df["team"].str.lower().str.contains(team_name.lower(), na=False)]
        if row.empty:
            match = _fuzzy_match(team_name, df["team"])
            if match:
                row = df[df["team"] == match]
        if row.empty:
            return None

        r = row.iloc[0]
        gp = max(float(r.get("games_played", 1)), 1)

        def per_game(col, fallback=0.0):
            val = r.get(col, fallback)
            try:
                return round(float(val) / gp, 3)
            except (TypeError, ValueError):
                return fallback

        # xG — present once FBref populates shooting tables (mid-season+), None until then
        def xg_col(col):
            val = r.get(col)
            try:
                return round(float(val) / gp, 3) if val is not None else None
            except (TypeError, ValueError):
                return None

        # Save% is stored as e.g. 72.5 — convert to 0.0–1.0 ratio
        raw_save_pct = r.get("Performance_Save%")
        try:
            save_pct = round(float(raw_save_pct) / 100, 3) if raw_save_pct is not None else 0.70
        except (TypeError, ValueError):
            save_pct = 0.70

        # long_shots: off-target shots per game as proxy (total shots - SOT)
        total_sh = r.get("Standard_Sh", 0)
        total_sot = r.get("Standard_SoT", 0)
        try:
            long_shots = round(max(0.0, (float(total_sh) - float(total_sot)) / gp), 2)
        except (TypeError, ValueError):
            long_shots = 4.0

        return {
            "goals_for":     per_game("Performance_Gls"),
            "sot_for":       per_game("Standard_SoT"),
            "goals_against": per_game("Performance_GA"),
            "sot_against":   per_game("Performance_SoTA"),
            "save_pct":      save_pct,
            "cards_yellow":  per_game("Performance_CrdY"),
            "crosses":       per_game("Performance_Crs"),
            "long_shots":    long_shots,
            "xg_for":        xg_col("Expected_xG"),
            "xg_against":    xg_col("Expected_xGA"),
        }

    def get_defensive_rank(self, team_name: str, league_id: int) -> int:
        """Ranks team 1–N by defensive actions (Int + TklW). Rank 1 = most defensive."""
        df = self._get_league_stats(league_id)
        if df is None:
            return 10

        try:
            df = df.copy()
            df["def_actions"] = (
                pd.to_numeric(df.get("Performance_Int", 0), errors="coerce").fillna(0) +
                pd.to_numeric(df.get("Performance_TklW", 0), errors="coerce").fillna(0)
            )
            df["block_rank"] = df["def_actions"].rank(ascending=False, method="min").astype(int)

            row = df[df["team"].str.lower() == team_name.lower()]
            if row.empty:
                row = df[df["team"].str.lower().str.contains(team_name.lower(), na=False)]
            if row.empty:
                match = _fuzzy_match(team_name, df["team"])
                if match:
                    row = df[df["team"] == match]
            if row.empty:
                return 10

            return int(row.iloc[0]["block_rank"])
        except Exception as e:
            print(f"[FBref] Failed to compute defensive rank for {team_name}: {e}")
            return 10
