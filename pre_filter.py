# Big 5 only — must match FOOTBALL_DATA_COMPETITIONS and LEAGUE_MAP in fbref_client
WHITELISTED_LEAGUES = {
    39:  "Premier League",
    140: "La Liga",
    78:  "Bundesliga",
    135: "Serie A",
    61:  "Ligue 1",
}


class PreFilter:
    def __init__(self):
        self.whitelisted_leagues = WHITELISTED_LEAGUES

    def filter_by_league(self, fixtures: list) -> list:
        """Stage 1 — Drop any fixture not in the top 10 leagues."""
        filtered = [f for f in fixtures if f.get("league_id") in self.whitelisted_leagues]
        dropped = len(fixtures) - len(filtered)
        print(f"[League Filter] {len(fixtures)} fixtures -> {len(filtered)} kept, {dropped} dropped")
        return filtered

    def filter_by_data_quality(self, fixtures: list) -> list:
        """Stage 2 — Drop any fixture where FBref returned no real stats for either team."""
        filtered = []
        for f in fixtures:
            if f.get("has_real_data"):
                filtered.append(f)
            else:
                print(f"[Data Filter] Dropped: {f['home_team']} vs {f['away_team']} - no FBref data yet")
        print(f"[Data Filter] {len(fixtures)} fixtures -> {len(filtered)} kept")
        return filtered

    def run(self, fixtures: list) -> list:
        """Run all filter stages in sequence."""
        print(f"\n{'='*50}")
        print(f"PRE-FILTER STARTING - {len(fixtures)} total fixtures")
        print(f"{'='*50}")
        fixtures = self.filter_by_league(fixtures)
        fixtures = self.filter_by_data_quality(fixtures)
        print(f"\n{len(fixtures)} matches passed all filters - ready for engine")
        print(f"{'='*50}\n")
        return fixtures
