import json
from pathlib import Path
from typing import Dict, Tuple
from itertools import product

import numpy as np
import pandas as pd

from elo import EloModel

def brier_score(pred_df: pd.DataFrame, actual_df: pd.DataFrame) -> float:
    home_win = (actual_df["Home_Team_Score"] > actual_df["Away_Team_Score"]).astype(float)
    draw = (actual_df["Home_Team_Score"] == actual_df["Away_Team_Score"]).astype(float)
    away_win = (actual_df["Home_Team_Score"] < actual_df["Away_Team_Score"]).astype(float)
    return ((pred_df["p_home_win"] - home_win) ** 2 + (pred_df["p_draw"] - draw) ** 2 + (pred_df["p_away_win"] - away_win) ** 2).mean()

def train_elo_model(train_df: pd.DataFrame, val_df: pd.DataFrame) -> Tuple[EloModel, Dict[str, float]]:
    K_values = [10, 20, 30, 40]
    home_adv_values = [50, 100, 150]
    nu_values = [0.10, 0.15, 0.20, 0.25]

    best = {"brier": float("inf"), "K": 20.0, "home_adv": 100.0, "nu": 0.15}

    for K, home_adv, nu in product(K_values, home_adv_values, nu_values):
        m = EloModel(K=float(K), home_adv=float(home_adv), nu=float(nu))
        for _, r in train_df.iterrows():
            m.update_ratings(r["Home"], r["Away"], int(r["Home_Team_Score"]), int(r["Away_Team_Score"]))
        preds = [m.predict(r["Home"], r["Away"]) for _, r in val_df.iterrows()]
        b = brier_score(pd.DataFrame(preds), val_df)
        if b < best["brier"]:
            best = {"brier": float(b), "K": float(K), "home_adv": float(home_adv), "nu": float(nu)}

    final = EloModel(K=best["K"], home_adv=best["home_adv"], nu=best["nu"])
    for _, r in train_df.iterrows():
        final.update_ratings(r["Home"], r["Away"], int(r["Home_Team_Score"]), int(r["Away_Team_Score"]))

    metrics = {"best_K": best["K"], "best_home_adv": best["home_adv"], "best_nu": best["nu"], "val_brier": best["brier"]}
    return final, metrics

def _load_channel_csv(channel_dir: Path) -> pd.DataFrame:
    csvs = list(channel_dir.glob("*.csv"))
    if not csvs:
        raise ValueError(f"No CSV files found in channel dir: {channel_dir}")
    return pd.read_csv(csvs[0])

def main() -> None:
    train_dir = Path("/opt/ml/input/data/train")
    val_dir = Path("/opt/ml/input/data/val")
    model_dir = Path("/opt/ml/model")
    model_dir.mkdir(parents=True, exist_ok=True)

    train_df = _load_channel_csv(train_dir)
    val_df = _load_channel_csv(val_dir)

    model, metrics = train_elo_model(train_df, val_df)

    import pickle
    with open(model_dir / "model.pkl", "wb") as f:
        pickle.dump(model, f)

    with open(model_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    main()
