import pandas as pd
import pytest
from pipeline.steps.preprocess import normalize_column_names, chronological_split, validate_data

def test_normalize_xg(sample_match_data):
    out = normalize_column_names(sample_match_data)
    assert "Away_Team_xG" in out.columns
    assert "Home_Team_xG.1" not in out.columns

def test_split_order(sample_match_data):
    train, val, test = chronological_split(sample_match_data, 0.7, 0.15)
    assert train["Date"].max() < val["Date"].min()
    assert val["Date"].max() < test["Date"].min()

def test_validate_missing_cols(sample_match_data):
    with pytest.raises(ValueError):
        validate_data(sample_match_data.drop(columns=["Home"]))
