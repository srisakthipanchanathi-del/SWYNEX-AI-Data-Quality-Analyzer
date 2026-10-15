"""SWYNEX AI Data Quality Analyzer.

Usage:
  python3 analyzer.py sample_data.csv
  python3 analyzer.py sample_data.csv --ground-truth ground_truth.csv
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score


def detect_outlier_rows(df: pd.DataFrame, exclude_columns=None):
    """Return row IDs flagged by an IQR rule for any numeric column."""
    exclude_columns = set(exclude_columns or [])
    numeric_cols = [
        c for c in df.select_dtypes(include=np.number).columns
        if c not in exclude_columns
    ]
    flagged = pd.Series(False, index=df.index)
    outlier_cells = {}
    for col in numeric_cols:
        values = pd.to_numeric(df[col], errors="coerce")
        non_missing = values.dropna()
        if non_missing.empty:
            continue
        q1, q3 = non_missing.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        col_flag = (values < lower) | (values > upper)
        flagged |= col_flag.fillna(False)
        outlier_cells[col] = {
            "lower_bound": float(lower),
            "upper_bound": float(upper),
            "flagged_values": int(col_flag.sum())
        }
    row_id_col = "record_id" if "record_id" in df.columns else None
    flagged_rows = df.loc[flagged, row_id_col].tolist() if row_id_col else df.index[flagged].tolist()
    return set(flagged_rows), outlier_cells, flagged


def analyze_csv(path: str, ground_truth_path=None):
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("The CSV has no rows.")
    row_count, col_count = df.shape
    missing_by_column = df.isna().sum().to_dict()
    rows_with_missing = int(df.isna().any(axis=1).sum())

    # Use record_id as a unique identifier if available; otherwise use all columns.
    duplicate_subset = [c for c in df.columns if c != "record_id"]
    duplicate_mask = df.duplicated(subset=duplicate_subset, keep="first")
    duplicate_count = int(duplicate_mask.sum())

    exclude = ["record_id"] if "record_id" in df.columns else []
    outlier_ids, outlier_details, outlier_mask = detect_outlier_rows(df, exclude)
    missing_cells = int(df.isna().sum().sum())
    total_cells = int(row_count * col_count)
    duplicate_share = duplicate_count / max(row_count, 1)
    outlier_cell_count = sum(item["flagged_values"] for item in outlier_details.values())
    outlier_cell_share = outlier_cell_count / max(total_cells, 1)
    missing_share = missing_cells / max(total_cells, 1)
    score = max(0.0, 100.0 * (1.0 - min(1.0, 0.50*missing_share + 0.30*duplicate_share + 0.20*outlier_cell_share)))

    report = {
        "file": str(path),
        "rows": int(row_count),
        "columns": int(col_count),
        "missing_cells": missing_cells,
        "missing_by_column": {k: int(v) for k, v in missing_by_column.items()},
        "rows_with_missing_values": rows_with_missing,
        "duplicate_rows": duplicate_count,
        "potential_outlier_rows": int(outlier_mask.sum()),
        "potential_outlier_row_ids": sorted(list(outlier_ids), key=str),
        "outlier_detection_bounds": outlier_details,
        "quality_score": round(score, 2),
        "score_note": "Project-defined heuristic; not an industry standard."
    }

    print("\n=== DATA QUALITY REPORT ===")
    print(f"File: {path}")
    print(f"Rows: {row_count} | Columns: {col_count}")
    print(f"Missing cells: {missing_cells}")
    print(f"Rows with missing values: {rows_with_missing}")
    print(f"Exact duplicate rows: {duplicate_count}")
    print(f"Rows with potential numeric outliers: {int(outlier_mask.sum())}")
    print(f"Data-quality score (heuristic): {score:.2f}/100")
    print("\nMissing values by column:")
    for col, count in missing_by_column.items():
        print(f"  {col}: {int(count)}")

    if ground_truth_path:
        truth = pd.read_csv(ground_truth_path)
        if "record_id" not in df.columns or "record_id" not in truth.columns or "has_injected_outlier" not in truth.columns:
            raise ValueError("Ground truth evaluation requires record_id and has_injected_outlier columns.")
        truth_map = truth.set_index("record_id")["has_injected_outlier"].to_dict()
        y_true = df["record_id"].map(truth_map).fillna(0).astype(int)
        y_pred = df["record_id"].isin(outlier_ids).astype(int)
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f = f1_score(y_true, y_pred, zero_division=0)
        report["outlier_evaluation"] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1_score": round(float(f), 4),
            "note": "Evaluated against deliberately injected outliers in a small synthetic dataset."
        }
        print("\nOutlier evaluation vs injected labels:")
        print(f"  Precision: {p:.3f}")
        print(f"  Recall:    {r:.3f}")
        print(f"  F1-score:  {f:.3f}")

    Path("quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nSaved quality_report.json")

    # Plot missing cells per column
    missing_series = pd.Series(missing_by_column).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    missing_series.plot(kind="bar", ax=ax)
    ax.set_title("Missing Values by Column")
    ax.set_ylabel("Number of missing cells")
    ax.set_xlabel("Column")
    fig.tight_layout()
    fig.savefig("outlier_summary.png", dpi=150)
    plt.close(fig)
    print("Saved outlier_summary.png")
    return report


def main():
    parser = argparse.ArgumentParser(description="Profile a CSV and flag common data-quality issues.")
    parser.add_argument("csv_path", help="Path to the CSV file to analyze")
    parser.add_argument("--ground-truth", help="Optional ground-truth CSV for demo outlier evaluation")
    args = parser.parse_args()
    analyze_csv(args.csv_path, args.ground_truth)


if __name__ == "__main__":
    main()
