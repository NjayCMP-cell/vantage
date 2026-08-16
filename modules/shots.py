class ShotsModule:
    def calculate(self, team: str, attack_sot: float, opp_conceded_sot: float,
                  keeper_save_pct: float, is_fast: bool, is_home: bool) -> dict:

        m_pace = 1.15 if is_fast else 0.90
        m_home = 1.10 if is_home else 0.95
        proj_sot = ((attack_sot + opp_conceded_sot) / 2.0) * m_pace * m_home
        proj_saves = proj_sot * keeper_save_pct
        proj_goals_conceded = proj_sot * (1.0 - keeper_save_pct)
        return {
            "team": team,
            "projected_sot": round(proj_sot, 2),
            "projected_gk_saves": round(proj_saves, 2),
            "projected_goals_conceded": round(proj_goals_conceded, 2),
        }
