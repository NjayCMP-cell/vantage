class CornersModule:
    def calculate(self, team: str, base_avg: float, speed_mps: float, crosses: float, formation: str,
                  possession: float, is_home: bool, long_shots: float, opp_block_rank: int, lead_dropoff: bool) -> dict:

        m_pace = 1.25 if speed_mps >= 1.9 else (0.80 if speed_mps <= 1.4 else 1.00)
        m_wing = 1.30 if formation in ["3-5-2", "5-3-2", "3-4-2-1"] or crosses >= 18.0 else (0.85 if crosses < 12.0 else 1.00)
        m_venue = 1.20 if possession >= 60.0 and is_home else (0.90 if possession >= 60.0 and not is_home else 1.00)
        m_blocks = 1.15 if long_shots >= 5.5 and opp_block_rank <= 5 else 1.00
        m_script = 0.85 if lead_dropoff and is_home else 1.00

        projected = base_avg * m_pace * m_wing * m_venue * m_blocks * m_script
        return {"team": team, "projected_corners": round(projected, 2)}
