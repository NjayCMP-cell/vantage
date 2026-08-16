from modules.goals import GoalAnalyticsModule
from modules.corners import CornersModule
from modules.cards import CardsModule
from modules.shots import ShotsModule
from modules.confidence import grade


class BetBuilderEngine:
    def __init__(self):
        self.goals = GoalAnalyticsModule()
        self.corners = CornersModule()
        self.cards = CardsModule()
        self.shots = ShotsModule()

    def analyze(self, match: dict) -> dict:
        # --- GOALS ---
        goals_result = self.goals.calculate_match_goals(
            home_team=match['home_team'],
            away_team=match['away_team'],
            home_xg_for=match['home_attack_xg'],
            home_goals_for=match['home_goals_scored'],
            home_xg_against=match['home_opp_xga'],
            away_xg_for=match['away_attack_xg'],
            away_goals_for=match['away_goals_scored'],
            away_xg_against=match['away_opp_xga'],
        )
        total_goals = goals_result['total_projected_goals']

        # --- CORNERS ---
        h_corners = self.corners.calculate(match['home_team'], match['home_base_corners'], match['direct_speed_mps'], match['home_crosses'], match['home_formation'], match['home_possession'], True, match['home_long_shots'], match['away_block_rank'], match['home_lead_dropoff'])
        a_corners = self.corners.calculate(match['away_team'], match['away_base_corners'], match['direct_speed_mps'], match['away_crosses'], match['away_formation'], match['away_possession'], False, match['away_long_shots'], match['home_block_rank'], False)
        total_corners = h_corners['projected_corners'] + a_corners['projected_corners']

        # --- CARDS ---
        cards = self.cards.calculate(match['home_avg_cards'], match['away_avg_cards'], match['ref_avg_cards'], match['is_derby'])

        # --- SHOTS ---
        h_shots = self.shots.calculate(match['home_team'], match['home_attack_sot'], match['away_conceded_sot'], match['home_save_pct'], match['direct_speed_mps'] >= 1.85, True)
        a_shots = self.shots.calculate(match['away_team'], match['away_attack_sot'], match['home_conceded_sot'], match['away_save_pct'], match['direct_speed_mps'] >= 1.85, False)
        combined_sot = h_shots['projected_sot'] + a_shots['projected_sot']

        # --- BET SLIP ---
        slip = goals_result['suggested_markets'][:]

        result = {
            "match": f"{match['home_team']} vs {match['away_team']}",
            "projected_goals": round(total_goals, 2),
            "projected_home_goals": goals_result['projected_home_goals'],
            "projected_away_goals": goals_result['projected_away_goals'],
            "projected_corners": round(total_corners, 2),
            "projected_home_corners": h_corners['projected_corners'],
            "projected_away_corners": a_corners['projected_corners'],
            "projected_cards": cards['projected_cards'],
            "projected_home_cards": cards['home_projected_cards'],
            "projected_away_cards": cards['away_projected_cards'],
            "projected_sot": round(combined_sot, 2),
            "home_projected_sot": h_shots['projected_sot'],
            "away_projected_sot": a_shots['projected_sot'],
            "home_gk_saves": a_shots['projected_gk_saves'],
            "away_gk_saves": h_shots['projected_gk_saves'],
            "bet_slip": slip,
        }
        result.update(grade(result))
        return result
