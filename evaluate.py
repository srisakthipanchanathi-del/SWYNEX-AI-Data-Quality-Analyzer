"""Evaluate SWYNEX detections against labelled synthetic data."""

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
)

from analyzer import detect_outlier_rows


LABELS = {
    "missing_values": "has_injected_missing",
    "outliers": "has_injected_outlier",
    "duplicates": "is_duplicate_copy",
}


def calculate_metrics(y_true, y_pred):
    return {
        "precision": round(
            float(precision_score(y_true, y_pred, zero_division=0)), 4
        ),
        "recall": round(
            float(recall_score(y_true, y_pred, zero_division=0)), 4
        ),
        "f1_score": round(
            float(f1_score(y_true, y_pred, zero_division=0)), 4
        ),
        "labelled_positive_cases": int(sum(y_true)),
        "predicted_positive_cases": int(sum(y_pred)),
    }


def evaluate_dataset(data_path="sample_data.csv",
                     truth_path="ground_truth.csv"):
    df = pd.read_csv(data_path)
    truth = pd.read_csv(truth_path)

    if df.empty or truth.empty:
        raise ValueError("Dataset and ground truth must not be empty.")

    for frame, name in ((df, "dataset"), (truth, "ground truth")):
        if "record_id" not in frame.columns:
            raise ValueError(f"{name} must contain record_id.")
        if frame["record_id"].duplicated().any():
            raise ValueError(f"{name} contains duplicate record_id values.")

    for label in LABELS.values():
        if label not in truth.columns:
            raise ValueError(f"Ground truth is missing column: {label}")

    if not set(df["record_id"]).issubset(set(truth["record_id"])):
        raise ValueError("Some dataset record IDs are absent from ground truth.")

    truth = truth.set_index("record_id")
    ids = df["record_id"]

    # Predictions are aligned to each record ID, not assumed row order.
    y_missing = df.isna().any(axis=1).astype(int).tolist()

    outlier_ids, _, _ = detect_outlier_rows(
        df, exclude_columns=["record_id"]
    )
    y_outlier = ids.isin(outlier_ids).astype(int).tolist()

    duplicate_subset = [c for c in df.columns if c != "record_id"]
    y_duplicate = df.duplicated(
        subset=duplicate_subset, keep="first"
    ).astype(int).tolist()

    predictions = {
        "missing_values": y_missing,
        "outliers": y_outlier,
        "duplicates": y_duplicate,
    }

    results = {}
    for issue, label in LABELS.items():
        y_true = truth.loc[ids, label].astype(int).tolist()
        y_pred = predictions[issue]
        results[issue] = calculate_metrics(y_true, y_pred)

    output = {
        "dataset": str(data_path),
        "records_evaluated": len(df),
        "results": results,
        "limitations": [
            "Results depend on the quality and coverage of synthetic labels.",
            "IQR outlier detection may flag legitimate rare values.",
            "Duplicate detection uses all columns except record_id.",
            "These metrics evaluate issue detection, not AI explanation quality.",
        ],
    }

    Path("evaluation_results.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    return output


if __name__ == "__main__":
    try:
        result = evaluate_dataset()
        print(json.dumps(result, indent=2))
        print("\nSaved evaluation_results.json")
    except (OSError, ValueError, KeyError, pd.errors.ParserError) as exc:
        raise SystemExit(f"Evaluation failed: {exc}")
