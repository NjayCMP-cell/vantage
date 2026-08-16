class CardsModule:
    def calculate(self, home_cards: float, away_cards: float, ref_cards: float, is_derby: bool) -> dict:

        m_ref   = 1.25 if ref_cards >= 5.2 else (0.75 if ref_cards <= 3.8 else 1.00)
        m_derby = 1.20 if is_derby else 1.00

        home_projected = home_cards * m_ref * m_derby
        away_projected = away_cards * m_ref * m_derby

        return {
            "home_projected_cards": round(home_projected, 2),
            "away_projected_cards": round(away_projected, 2),
            "projected_cards":      round(home_projected + away_projected, 2),
        }
