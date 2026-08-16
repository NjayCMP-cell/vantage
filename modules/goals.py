class GoalAnalyticsModule:

    @staticmethod
    def calculate_match_goals(
        home_team: str,
        away_team: str,
        home_xg_for: float,
        home_goals_for: float,
        home_xg_against: float,
        away_xg_for: float,
        away_goals_for: float,
        away_xg_against: float,
    ) -> dict:

        # 1. Base expected goals
        raw_home_exp = (home_xg_for + away_xg_against) / 2.0
        raw_away_exp = (away_xg_for + home_xg_against) / 2.0

        # 2. Conversion efficiency — capped 0.75x to 1.25x
        home_conv = max(0.75, min(1.25, home_goals_for / home_xg_for if home_xg_for > 0 else 1.0))
        away_conv = max(0.75, min(1.25, away_goals_for / away_xg_for if away_xg_for > 0 else 1.0))

        # 3. Venue multipliers
        proj_home_goals = raw_home_exp * home_conv * 1.08
        proj_away_goals = raw_away_exp * away_conv * 0.92
        total_proj_goals = proj_home_goals + proj_away_goals

        # 4. Market flags
        markets = []
        if total_proj_goals >= 2.70:
            markets.append("Over 2.5 Match Goals")
        elif total_proj_goals >= 1.85:
            markets.append("Over 1.5 Match Goals")
        else:
            markets.append("Under 2.5 Match Goals")

        if proj_home_goals >= 1.55:
            markets.append(f"{home_team} Over 1.5 Team Goals")
        if proj_away_goals >= 1.35:
            markets.append(f"{away_team} Over 0.5 Team Goals")

        return {
            "match": f"{home_team} vs {away_team}",
            "projected_home_goals": round(proj_home_goals, 2),
            "projected_away_goals": round(proj_away_goals, 2),
            "total_projected_goals": round(total_proj_goals, 2),
            "suggested_markets": markets,
        }
