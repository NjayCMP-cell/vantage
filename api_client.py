import os
import requests
from datetime import date
from dotenv import load_dotenv
from fbref_client import FBrefClient
from understat_client import UnderstatClient

load_dotenv()

# ============================================================
# football-data.org — fixture fetch (unlimited daily)
# ============================================================
FOOTBALL_DATA_API_KEY = os.environ["FOOTBALL_DATA_API_KEY"]
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
FOOTBALL_DATA_HEADERS = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

# football-data.org competition IDs — Big 5 only (FBref coverage)
FOOTBALL_DATA_COMPETITIONS = {
    "PL":  39,   # Premier League
    "PD":  140,  # La Liga
    "BL1": 78,   # Bundesliga
    "SA":  135,  # Serie A
    "FL1": 61,   # Ligue 1
}

# ============================================================
# API-Football (api-sports.io) — kept for reference, currently unused
# ============================================================
API_FOOTBALL_KEY = os.environ["API_FOOTBALL_KEY"]
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

WHITELISTED_LEAGUE_IDS = list(FOOTBALL_DATA_COMPETITIONS.values())


class FootballDataClient:
    """Fetches today's fixtures from football-data.org — unlimited daily calls."""

    def _get(self, endpoint: str, params: dict = {}) -> dict:
        url = f"{FOOTBALL_DATA_BASE_URL}/{endpoint}"
        response = requests.get(url, headers=FOOTBALL_DATA_HEADERS, params=params)
        if response.status_code != 200:
            raise Exception(f"[football-data.org] Error {response.status_code}: {response.text}")
        return response.json()

    def get_todays_fixtures(self) -> list:
        """Fetch all fixtures scheduled for today across whitelisted competitions."""
        today = date.today().isoformat()
        print(f"[football-data.org] Fetching fixtures for {today}...")
        fixtures = []
        for comp_code, league_id in FOOTBALL_DATA_COMPETITIONS.items():
            try:
                data = self._get(f"competitions/{comp_code}/matches", {"dateFrom": today, "dateTo": today})
                for match in data.get("matches", []):
                    if match.get("status") in ("SCHEDULED", "TIMED", "FRIENDLY"):
                        fixtures.append({
                            "fixture_id": match["id"],
                            "league_id": league_id,
                            "competition_code": comp_code,
                            "home_team": match["homeTeam"]["name"],
                            "away_team": match["awayTeam"]["name"],
                            "home_team_id": match["homeTeam"]["id"],
                            "away_team_id": match["awayTeam"]["id"],
                            "season": date.today().year,
                        })
            except Exception as e:
                print(f"[football-data.org] Skipped {comp_code}: {e}")
        print(f"[football-data.org] Found {len(fixtures)} fixtures today")
        return fixtures


class APIFootballClient:
    """
    Fetches deep team stats from api-sports.io.
    Uses /teams/statistics — 2 calls per match (home + away).
    Does NOT loop through individual past fixtures.
    """

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{API_FOOTBALL_BASE_URL}/{endpoint}"
        response = requests.get(url, headers=API_FOOTBALL_HEADERS, params=params)
        if response.status_code != 200:
            raise Exception(f"[API-Football] Error {response.status_code}: {response.text}")
        return response.json()

    def get_team_stats(self, team_id: int, league_id: int, season: int) -> dict:
        """One call — returns full season averages for a team: goals, corners, cards, SOT, possession."""
        data = self._get("teams/statistics", {"team": team_id, "league": league_id, "season": season})
        return data.get("response", {})


class FixtureMapper:
    """
    Builds match_data dicts for the engine using:
    - football-data.org for fixture list
    - FBrefClient for season stats + possession/formation
    - UnderstatClient for per-match xG
    """

    def __init__(self):
        self.fd_client = FootballDataClient()
        self.fbref = FBrefClient()
        self.understat = UnderstatClient()

    def build_match_data(self, fixture: dict) -> dict | None:
        home = fixture["home_team"]
        away = fixture["away_team"]
        league_id = fixture["league_id"]

        # Season stats (goals, SOT, cards, save_pct, crosses, long_shots)
        h_stats = self.fbref.get_team_stats(home, league_id) or {}
        a_stats = self.fbref.get_team_stats(away, league_id) or {}

        # Defensive rank (Int + TklW league ranking)
        h_block_rank = self.fbref.get_defensive_rank(home, league_id)
        a_block_rank = self.fbref.get_defensive_rank(away, league_id)

        # Possession + formation
        h_pf = self.fbref.get_possession_and_formation(home, league_id)
        a_pf = self.fbref.get_possession_and_formation(away, league_id)

        # xG — Understat first, FBref xG fallback, then hardcoded defaults
        h_xg = self.understat.get_team_xg_stats(home, league_id, fbref_stats=h_stats)
        a_xg = self.understat.get_team_xg_stats(away, league_id, fbref_stats=a_stats)

        home_goals = h_stats.get("goals_for", 1.5)
        away_goals = a_stats.get("goals_for", 1.2)
        home_xg_for = h_xg["xg_for"]
        away_xg_for = a_xg["xg_for"]

        has_real_data = h_stats is not None and a_stats is not None

        return {
            "fixture_id": fixture["fixture_id"],
            "league_id": league_id,
            "home_team": home,
            "away_team": away,
            "has_real_data": has_real_data,

            # Goals / xG (keys match engine.py)
            "home_attack_xg":      home_xg_for,
            "home_opp_xga":        h_xg["xg_against"],
            "home_goals_scored":   home_goals,
            "home_missing_finisher": False,
            "away_attack_xg":      away_xg_for,
            "away_opp_xga":        a_xg["xg_against"],
            "away_goals_scored":   away_goals,
            "away_missing_finisher": False,

            # Corners (crosses as proxy — no direct source)
            "home_base_corners":  h_stats.get("crosses", 15.0),
            "away_base_corners":  a_stats.get("crosses", 12.0),
            "direct_speed_mps":   1.85,
            "home_crosses":       h_stats.get("crosses", 15.0),
            "away_crosses":       a_stats.get("crosses", 12.0),
            "home_long_shots":    h_stats.get("long_shots", 4.0),
            "away_long_shots":    a_stats.get("long_shots", 3.5),
            "home_block_rank":    h_block_rank,
            "away_block_rank":    a_block_rank,
            "home_lead_dropoff":  False,

            # Possession + formation (real data)
            "home_formation":   h_pf["formation"],
            "away_formation":   a_pf["formation"],
            "home_possession":  h_pf["possession"],
            "away_possession":  a_pf["possession"],

            # Cards
            "home_avg_cards": h_stats.get("cards_yellow", 2.0),
            "away_avg_cards": a_stats.get("cards_yellow", 2.2),
            "ref_avg_cards":  4.5,
            "is_derby":       False,

            # Shots
            "home_attack_sot":    h_stats.get("sot_for", 4.5),
            "away_conceded_sot":  a_stats.get("sot_against", 4.0),
            "home_save_pct":      h_stats.get("save_pct", 0.70),
            "away_attack_sot":    a_stats.get("sot_for", 3.8),
            "home_conceded_sot":  h_stats.get("sot_against", 4.0),
            "away_save_pct":      a_stats.get("save_pct", 0.70),
        }
