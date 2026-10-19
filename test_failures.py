import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from analyzer import analyze_csv
from ai_explainer import load_report, explain_report
from evaluate import evaluate_dataset


class TestSWYNEXFailures(unittest.TestCase):

    def test_missing_csv(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            analyze_csv("missing_file_123.csv")

    def test_empty_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.csv"
            path.write_text("record_id,value\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                analyze_csv(str(path))

    def test_missing_report(self):
        with self.assertRaises(FileNotFoundError):
            load_report("missing_report_123.json")

    def test_invalid_json_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text("{invalid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_report(path)

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                explain_report("unused_report.json")

    def test_missing_ground_truth(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            evaluate_dataset(
                "sample_data.csv",
                "missing_ground_truth_123.csv",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
