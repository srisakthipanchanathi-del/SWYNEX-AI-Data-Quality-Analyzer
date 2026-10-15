# SWYNEX AI Data Quality Analyzer

A small, reproducible Python project that profiles a CSV file and flags common data-quality issues before analysis or machine-learning use.

## Problem statement
Analysts can waste time training models on datasets containing missing values, duplicate records, or unusual numeric values. This prototype scans a CSV and produces a concise quality report so a person can review issues before using the data.

## Intended user
Students, data analysts, and ML practitioners who need a first-pass check of tabular data.

## What it checks
- Missing values per column and rows containing missing values
- Exact duplicate records (excluding the unique `record_id` field when present)
- Potential numerical outliers using the interquartile range (IQR) rule
- A transparent data-quality score based on the proportion of cells that are missing, duplicate-row share, and numeric outlier-cell share

The score is a simple project-defined indicator, not an industry standard or a guarantee that a dataset is suitable for modelling.

## Data source
`sample_data.csv` is a synthetic demonstration dataset generated for this project. It contains 105 rows, with deliberately injected missing values, numeric outliers, and duplicate copies. It contains no real personal data. `ground_truth.csv` records which row IDs were deliberately modified, allowing a basic evaluation on this known demo dataset.

## Success criteria
The prototype is evaluated against the known injected issues:
- Report missing-value counts accurately.
- Identify exact duplicate copies.
- Detect the deliberately injected numeric outliers using the documented IQR rule.
- Report precision and recall for the outlier detector against the injected outlier labels.

Targets: at least 90% precision and 80% recall for injected outliers on this sample. These are targets, not guaranteed results. Since the dataset is small and synthetic, performance does not establish real-world generalization.

## Method
1. Load the CSV with Pandas.
2. Calculate missing-value counts and duplicate rows.
3. For numeric columns, flag values outside Q1 − 1.5×IQR and Q3 + 1.5×IQR.
4. Calculate a simple transparent quality score.
5. On the included sample dataset, compare detected outlier row IDs with `ground_truth.csv` and print precision/recall/F1.

## Run locally
Requires Python 3.10+.

```bash
python3 -m pip install -r requirements.txt
python3 analyzer.py sample_data.csv
```

For evaluation against the bundled ground truth:

```bash
python3 analyzer.py sample_data.csv --ground-truth ground_truth.csv
```

To analyze your own CSV, pass its path:

```bash
python3 analyzer.py path/to/your_data.csv
```

The script writes `quality_report.json` and `outlier_summary.png` in the current directory. Review flags before deleting or modifying any data.

## Limitations and responsible use
- IQR flags unusual values, not necessarily errors; legitimate extreme values can be flagged.
- Exact duplicates are detected using all columns except `record_id` when present. Similar-but-not-identical records are not detected.
- The quality score is a simple heuristic and should not be treated as a universal benchmark.
- The demo data is synthetic and small. Test on representative, authorized data before relying on the tool.
- The tool does not automatically delete, impute, or correct records. Human review is required.

## Files
- `analyzer.py` — CSV analysis and evaluation
- `sample_data.csv` — synthetic sample data with injected issues
- `ground_truth.csv` — labels for injected issues in the demo
- `requirements.txt` — dependencies
