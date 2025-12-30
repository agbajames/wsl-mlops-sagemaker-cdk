import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def sample_match_data():
    return pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=20, freq="W"),
        "Time": ["19:45"] * 20,
        "Home": ["Arsenal", "Chelsea"] * 10,
        "Away": ["Chelsea", "Arsenal"] * 10,
        "Home_Team_Score": [2, 1, 3, 0, 1, 2, 2, 1, 0, 1] * 2,
        "Away_Team_Score": [1, 2, 0, 3, 1, 1, 0, 2, 2, 1] * 2,
        "Home_Team_xG": [1.8, 1.2, 2.5, 0.8, 1.1, 1.9, 2.1, 1.0, 0.7, 1.3] * 2,
        "Home_Team_xG.1": [0.9, 1.5, 0.6, 2.3, 1.0, 1.1, 0.5, 1.8, 2.0, 1.2] * 2,
    })

@pytest.fixture(autouse=True)
def reset_seed():
    np.random.seed(42)
