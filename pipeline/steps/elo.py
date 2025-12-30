from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

def expected_score(r_home: float, r_away: float, home_adv: float = 100.0) -> float:
    """Standard Elo expected score for the home team.

The +home_adv shifts the home team's effective rating.
"""
    return 1.0 / (1.0 + 10.0 ** ((r_away - (r_home + home_adv)) / 400.0))

def davidson_wdl_probs(r_home: float, r_away: float, home_adv: float = 100.0, nu: float = 0.15) -> Dict[str, float]:
    """Davidson model (Bradley–Terry with ties).

Let a_i be team strength. For ratings, use a=10^(r/400).
P(home) = a_h / (a_h + a_a + 2*nu*sqrt(a_h*a_a))
P(away) = a_a / (a_h + a_a + 2*nu*sqrt(a_h*a_a))
P(draw) = 2*nu*sqrt(a_h*a_a) / denom

home_adv is applied as rating boost to home team.
"""
    a_h = 10.0 ** ((r_home + home_adv) / 400.0)
    a_a = 10.0 ** (r_away / 400.0)
    tie = 2.0 * max(nu, 0.0) * math.sqrt(a_h * a_a)
    denom = a_h + a_a + tie
    p_home = a_h / denom
    p_away = a_a / denom
    p_draw = tie / denom
    return {"p_home_win": p_home, "p_draw": p_draw, "p_away_win": p_away}

@dataclass
class EloModel:
    initial_rating: float = 1500.0
    K: float = 20.0
    home_adv: float = 100.0
    nu: float = 0.15
    ratings: Dict[str, float] = field(default_factory=dict)

    def get_rating(self, team: str) -> float:
        return float(self.ratings.get(team, self.initial_rating))

    def update_ratings(self, home_team: str, away_team: str, home_score: int, away_score: int) -> None:
        r_h = self.get_rating(home_team)
        r_a = self.get_rating(away_team)

        exp_h = expected_score(r_h, r_a, self.home_adv)
        exp_a = 1.0 - exp_h

        if home_score > away_score:
            act_h, act_a = 1.0, 0.0
        elif home_score < away_score:
            act_h, act_a = 0.0, 1.0
        else:
            act_h, act_a = 0.5, 0.5

        self.ratings[home_team] = r_h + self.K * (act_h - exp_h)
        self.ratings[away_team] = r_a + self.K * (act_a - exp_a)

    def predict(self, home_team: str, away_team: str) -> Dict[str, float]:
        r_h = self.get_rating(home_team)
        r_a = self.get_rating(away_team)
        probs = davidson_wdl_probs(r_h, r_a, self.home_adv, self.nu)
        probs["r_home"] = r_h
        probs["r_away"] = r_a
        return probs
