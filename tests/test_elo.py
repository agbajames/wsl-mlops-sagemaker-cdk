import pytest
from pipeline.steps.elo import EloModel, davidson_wdl_probs, expected_score

def test_expected_score_equal_no_adv():
    assert expected_score(1500, 1500, home_adv=0) == pytest.approx(0.5, abs=0.01)

def test_expected_score_equal_with_adv():
    assert expected_score(1500, 1500, home_adv=100) == pytest.approx(0.64, abs=0.05)

def test_probs_sum_to_one():
    probs = davidson_wdl_probs(1520, 1480, home_adv=100, nu=0.15)
    assert (probs["p_home_win"] + probs["p_draw"] + probs["p_away_win"]) == pytest.approx(1.0, abs=1e-9)

def test_nu_increases_draws():
    low = davidson_wdl_probs(1500, 1500, home_adv=0, nu=0.05)["p_draw"]
    high = davidson_wdl_probs(1500, 1500, home_adv=0, nu=0.30)["p_draw"]
    assert high > low

def test_elo_update_home_win_moves_ratings():
    m = EloModel(initial_rating=1500, K=20, home_adv=100)
    m.update_ratings("Arsenal", "Chelsea", 2, 0)
    assert m.get_rating("Arsenal") > 1500
    assert m.get_rating("Chelsea") < 1500
