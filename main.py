from engine import BetBuilderEngine
from pre_filter import PreFilter
from api_client import FixtureMapper
from firestore_push import push_results

# ============================================================
# MODE SWITCH — change to True when API key is ready
# ============================================================
LIVE_MODE = True
# ============================================================

engine = BetBuilderEngine()
pre_filter = PreFilter()

if LIVE_MODE:
    # --- LIVE MODE — football-data.org fixtures → API-Football deep stats ---
    print("Running in LIVE MODE...")
    mapper = FixtureMapper()
    raw_fixtures = mapper.fd_client.get_todays_fixtures()
    fixtures = []
    for raw in raw_fixtures:
        match_data = mapper.build_match_data(raw)
        if match_data:
            fixtures.append(match_data)
else:
    # --- MOCK MODE — hardcoded sample data for testing ---
    print("Running in MOCK MODE...")
    fixtures = [
        {
            "fixture_id": 1,
            "league_id": 135,
            "home_team": "Atalanta",
            "away_team": "Fiorentina",
            "has_real_data": True,
            "home_attack_xg": 1.95, "away_opp_xga": 1.40, "home_goals_scored": 2.10, "home_missing_finisher": False,
            "away_attack_xg": 1.20, "home_opp_xga": 1.10, "away_goals_scored": 1.15, "away_missing_finisher": False,
            "home_base_corners": 5.8, "away_base_corners": 4.2, "direct_speed_mps": 2.05,
            "home_crosses": 21.0, "away_crosses": 11.5, "home_formation": "3-5-2", "away_formation": "4-3-3",
            "home_possession": 56.0, "away_possession": 44.0, "home_long_shots": 6.2, "away_long_shots": 3.8,
            "home_block_rank": 8, "away_block_rank": 3, "home_lead_dropoff": False,
            "home_avg_cards": 2.2, "away_avg_cards": 2.6, "ref_avg_cards": 5.1, "is_derby": True,
            "home_attack_sot": 5.2, "away_conceded_sot": 4.8, "home_save_pct": 0.72,
            "away_attack_sot": 3.9, "home_conceded_sot": 4.1, "away_save_pct": 0.68,
        },
        {
            "fixture_id": 2,
            "league_id": 39,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "has_real_data": True,
            "home_attack_xg": 2.10, "away_opp_xga": 1.55, "home_goals_scored": 2.30, "home_missing_finisher": False,
            "away_attack_xg": 1.40, "home_opp_xga": 1.20, "away_goals_scored": 1.30, "away_missing_finisher": True,
            "home_base_corners": 6.2, "away_base_corners": 4.8, "direct_speed_mps": 1.95,
            "home_crosses": 19.0, "away_crosses": 13.0, "home_formation": "4-3-3", "away_formation": "4-2-3-1",
            "home_possession": 62.0, "away_possession": 38.0, "home_long_shots": 5.8, "away_long_shots": 4.1,
            "home_block_rank": 6, "away_block_rank": 4, "home_lead_dropoff": True,
            "home_avg_cards": 1.8, "away_avg_cards": 2.4, "ref_avg_cards": 4.9, "is_derby": True,
            "home_attack_sot": 6.1, "away_conceded_sot": 5.2, "home_save_pct": 0.74,
            "away_attack_sot": 4.2, "home_conceded_sot": 4.8, "away_save_pct": 0.71,
        },
    ]

# --- RUN PRE-FILTER ---
qualified = pre_filter.run(fixtures)

# --- RUN ENGINE ---
results = []
for fixture in qualified:
    result = engine.analyze(fixture)
    result["fixture_id"] = fixture["fixture_id"]
    results.append(result)

# --- SORT BY CONFIDENCE SCORE ---
results.sort(key=lambda x: x["confidence_score"], reverse=True)

# --- PUSH TO FIRESTORE ---
if results:
    push_results(results)

# --- PRINT RESULTS ---
print("\nFINAL MATCH ANALYSIS - RANKED BY CONFIDENCE SCORE")
print("=" * 55)
for result in results:
    print(f"\n  {result['match']}")
    print(f"  Confidence Score : {result['confidence_score']} / 100  [{result['grade']}]")
    print(f"  Projected Goals  : {result['projected_goals']}")
    print(f"  Projected Corners: {result['projected_corners']}")
    print(f"  Projected Cards  : {result['projected_cards']}")
    print(f"  Home SOT         : {result['home_projected_sot']}")
    print(f"  Away SOT         : {result['away_projected_sot']}")
    print(f"  BET SLIP:")
    for bet in result['bet_slip']:
        print(f"    - {bet}")
    print("-" * 55)
