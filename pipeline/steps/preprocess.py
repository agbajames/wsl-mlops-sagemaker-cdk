import argparse
from pathlib import Path
from typing import Tuple
import warnings

import pandas as pd

REQUIRED_COLS = ["Date", "Home", "Away", "Home_Team_Score", "Away_Team_Score"]

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Home_Team_xG.1" in df.columns and "Away_Team_xG" not in df.columns:
        df = df.rename(columns={"Home_Team_xG.1": "Away_Team_xG"})
    return df

def validate_data(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df[REQUIRED_COLS].isnull().any().any():
        raise ValueError("Null values found in required columns")
    if (df["Home_Team_Score"] < 0).any() or (df["Away_Team_Score"] < 0).any():
        raise ValueError("Negative scores found")
    if not pd.to_datetime(df["Date"], errors="coerce").notnull().all():
        raise ValueError("Date column contains invalid dates")
    if not pd.to_datetime(df["Date"]).is_monotonic_increasing:
        warnings.warn("Dates are not sorted. Sorting chronologically.", UserWarning)

def chronological_split(df: pd.DataFrame, train_pct: float = 0.7, val_pct: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        raise ValueError("Cannot split empty DataFrame")
    if train_pct <= 0 or val_pct <= 0 or (train_pct + val_pct) >= 1.0:
        raise ValueError("Invalid split percentages")
    df = df.sort_values("Date").reset_index(drop=True)
    n = len(df)
    train_end = int(n * train_pct)
    val_end = int(n * (train_pct + val_pct))
    return df.iloc[:train_end].copy(), df.iloc[train_end:val_end].copy(), df.iloc[val_end:].copy()

def preprocess_pipeline(df: pd.DataFrame, train_pct: float = 0.7, val_pct: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = normalize_column_names(df)
    df["Date"] = pd.to_datetime(df["Date"])
    validate_data(df)
    return chronological_split(df, train_pct=train_pct, val_pct=val_pct)

def _find_single_csv(input_dir: Path) -> Path:
    csvs = list(input_dir.glob("*.csv"))
    if len(csvs) != 1:
        raise ValueError(f"Expected exactly 1 CSV in {input_dir}, found: {[c.name for c in csvs]}")
    return csvs[0]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-pct", type=float, default=0.7)
    ap.add_argument("--val-pct", type=float, default=0.15)
    args = ap.parse_args()

    input_dir = Path("/opt/ml/processing/input")
    train_dir = Path("/opt/ml/processing/train")
    val_dir = Path("/opt/ml/processing/val")
    test_dir = Path("/opt/ml/processing/test")
    for d in [train_dir, val_dir, test_dir]:
        d.mkdir(parents=True, exist_ok=True)

    csv_path = _find_single_csv(input_dir)
    df = pd.read_csv(csv_path)
    train, val, test = preprocess_pipeline(df, train_pct=args.train_pct, val_pct=args.val_pct)

    train.to_csv(train_dir / "train.csv", index=False)
    val.to_csv(val_dir / "val.csv", index=False)
    test.to_csv(test_dir / "test.csv", index=False)

if __name__ == "__main__":
    main()
