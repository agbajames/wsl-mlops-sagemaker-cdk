import argparse
import json
import tarfile
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from train import brier_score
from elo import EloModel

def log_loss(pred_df: pd.DataFrame, actual_df: pd.DataFrame) -> float:
    eps = 1e-15
    home_win = (actual_df["Home_Team_Score"] > actual_df["Away_Team_Score"]).astype(float)
    draw = (actual_df["Home_Team_Score"] == actual_df["Away_Team_Score"]).astype(float)
    away_win = (actual_df["Home_Team_Score"] < actual_df["Away_Team_Score"]).astype(float)
    return -(
        home_win * np.log(pred_df["p_home_win"].clip(eps, 1 - eps))
        + draw * np.log(pred_df["p_draw"].clip(eps, 1 - eps))
        + away_win * np.log(pred_df["p_away_win"].clip(eps, 1 - eps))
    ).mean()

def accuracy(pred_df: pd.DataFrame, actual_df: pd.DataFrame) -> float:
    pred_idx = pred_df[["p_home_win", "p_draw", "p_away_win"]].values.argmax(axis=1)
    actual_idx = []
    for _, r in actual_df.iterrows():
        if r["Home_Team_Score"] > r["Away_Team_Score"]:
            actual_idx.append(0)
        elif r["Home_Team_Score"] == r["Away_Team_Score"]:
            actual_idx.append(1)
        else:
            actual_idx.append(2)
    return float((pred_idx == np.array(actual_idx)).mean())

def evaluate_model(model: EloModel, test_df: pd.DataFrame) -> Dict[str, float]:
    preds = []
    for _, r in test_df.iterrows():
        preds.append(model.predict(r["Home"], r["Away"]))
        model.update_ratings(r["Home"], r["Away"], int(r["Home_Team_Score"]), int(r["Away_Team_Score"]))
    pred_df = pd.DataFrame(preds)
    return {
        "test_brier": float(brier_score(pred_df, test_df)),
        "test_log_loss": float(log_loss(pred_df, test_df)),
        "accuracy": float(accuracy(pred_df, test_df)),
    }

def _extract_model(model_tar: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(model_tar, "r:gz") as tf:
        tf.extractall(out_dir)
    pkl = out_dir / "model.pkl"
    if not pkl.exists():
        raise FileNotFoundError("model.pkl not found in extracted model artifacts")
    return pkl

def main() -> None:
    model_input = Path("/opt/ml/processing/model")
    test_input = Path("/opt/ml/processing/test")
    out_dir = Path("/opt/ml/processing/evaluation")
    out_dir.mkdir(parents=True, exist_ok=True)

    model_tar = next(model_input.glob("*.tar.gz"))
    extracted_dir = out_dir / "_model"
    model_pkl = _extract_model(model_tar, extracted_dir)

    import pickle
    with open(model_pkl, "rb") as f:
        model = pickle.load(f)

    test_csv = next(test_input.glob("*.csv"))
    test_df = pd.read_csv(test_csv)

    metrics = evaluate_model(model, test_df)

    with open(out_dir / "evaluation.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    main()
