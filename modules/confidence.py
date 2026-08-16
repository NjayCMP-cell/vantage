STATS = [
    ("projected_goals",       2.5,  5.5),
    ("projected_home_goals",  1.5,  3.5),
    ("projected_away_goals",  1.5,  3.5),
    ("projected_corners",     7.5, 12.5),
    ("projected_home_corners",4.5,  7.5),
    ("projected_away_corners",3.5,  6.5),
    ("projected_cards",       2.5,  5.5),
    ("projected_home_cards",  1.5,  3.5),
    ("projected_away_cards",  1.5,  3.5),
    ("projected_sot",         9.5,  None),
    ("home_projected_sot",    6.5,  None),
    ("away_projected_sot",    6.5,  None),
]

POINTS_EACH = 100 / len(STATS)  # 8.333...


def _score_stat(value: float, over_line: float, under_line) -> tuple[float, str]:
    """Returns (points, direction) for one stat."""
    over_score = min((value / over_line) * POINTS_EACH, POINTS_EACH)

    if under_line is not None:
        under_score = min((under_line / value) * POINTS_EACH, POINTS_EACH)
    else:
        under_score = 0.0

    if over_score >= under_score:
        return over_score, "over"
    return under_score, "under"


def grade(engine_output: dict) -> dict:
    total = 0.0
    breakdown = {}

    for key, over_line, under_line in STATS:
        value = engine_output.get(key, 0.0) or 0.0
        points, direction = _score_stat(value, over_line, under_line)
        total += points
        breakdown[key] = {"value": round(value, 2), "points": round(points, 2), "direction": direction}

    total = round(total, 1)

    if total >= 75:
        grade_label = "Sweet Spot"
    elif total >= 60:
        grade_label = "Excitement"
    else:
        grade_label = "Daily Sheet"

    return {
        "confidence_score": total,
        "grade": grade_label,
        "breakdown": breakdown,
    }
