"""
Scoring system for World Cup predictions.

Points:
  3 pts — Exact score (e.g. 2-1 predicted and 2-1 final)
  2 pts — Correct goal difference (e.g. 2-0 predicted and 3-1 final → both team1 wins by 1)
  1 pt  — Correct winner only
  +1 pt — Correct penalty shootout winner (if applicable)
  0 pts — Wrong result
"""


def calculate_points(
    pred1: int, pred2: int, pred_pen: int | None,
    actual1: int, actual2: int, actual_pen: int | None
) -> int:
    points = 0

    # Determine outcomes
    def outcome(s1, s2):
        if s1 > s2:
            return 1
        elif s2 > s1:
            return 2
        return 0  # draw

    pred_outcome = outcome(pred1, pred2)
    actual_outcome = outcome(actual1, actual2)

    if pred1 == actual1 and pred2 == actual2:
        # Exact score
        points += 3
    elif pred_outcome == actual_outcome:
        # Correct outcome — check goal difference
        pred_diff = pred1 - pred2
        actual_diff = actual1 - actual2
        if pred_diff == actual_diff:
            points += 2
        else:
            points += 1
    else:
        # Wrong result — no points
        return 0

    # Penalty winner bonus
    if actual_pen and pred_pen and pred_pen == actual_pen:
        points += 1

    return points
