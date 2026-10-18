
"""
SWYNEX AI Data Quality Explainer
Task 2: Gemini API Integration

Reads the existing data-quality report, sends it to Gemini
through the Interactions REST API, and saves the explanation.
"""

import json
import os
import sys
from pathlib import Path

import requests

MODEL_NAME = "gemini-3.8-flash"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/interactions"
)


def load_report(report_path):
    """Load the existing JSON quality report."""

    path = Path(report_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report not found: {path}. "
            "Run analyzer.py first."
        )

    with path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    if not isinstance(report, dict):
        raise ValueError("The report must be a JSON object.")

    return report


def create_prompt(report):
    """Create instructions for the AI model."""

    return f"""
You are SWYNEX, an AI data-quality analyst.

Explain the following data-quality report to a beginner.

Use these sections:

1. Overall Data Quality Assessment
2. Missing Values and Their Impact
3. Duplicate Records
4. Potential Outliers
5. Three Prioritized Recommendations
6. Limitations and Validation Steps

Important rules:
- Use only facts supported by the report.
- Do not invent statistics or column names.
- State when information is unavailable.
- Potential outliers are not necessarily errors.
- Do not recommend deleting records without validation.
- Explain recommendations in simple, practical language.

DATA QUALITY REPORT:
{json.dumps(report, indent=2, default=str)}
"""


def extract_text(data):
    """Extract generated text from the API response."""

    # Some responses expose the complete text directly.
    output_text = data.get("output_text")

    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts = []

    def collect(obj):
        if isinstance(obj, dict):
            # Capture explicit text blocks.
            if (
                obj.get("type") == "text"
                and isinstance(obj.get("text"), str)
            ):
                parts.append(obj["text"])

            # Handle message-style content blocks.
            if (
                obj.get("type") == "output_text"
                and isinstance(obj.get("text"), str)
            ):
                parts.append(obj["text"])

            for key, value in obj.items():
                if key not in ("text",):
                    collect(value)

        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(data.get("steps", []))
    collect(data.get("outputs", []))

    # Remove duplicate blocks while preserving their order.
    unique_parts = list(dict.fromkeys(
        part.strip() for part in parts if part.strip()
    ))

    return "\n\n".join(unique_parts)


def explain_report(report_path="quality_report.json"):
    """Generate an explanation through the Gemini REST API."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            'GEMINI_API_KEY is missing. Set it using:\n'
            'export GEMINI_API_KEY="YOUR_API_KEY"'
        )

    report = load_report(report_path)
    prompt = create_prompt(report)

    response = requests.post(
        API_URL,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "input": prompt,
        },
        timeout=120,
    )

    if not response.ok:
        # Do not print the API key or request headers.
        raise RuntimeError(
            f"Gemini API returned HTTP {response.status_code}: "
            f"{response.text[:1500]}"
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "Gemini returned an invalid JSON response."
        ) from error

    explanation = extract_text(data)

    if not explanation:
        # Show a short response preview to help diagnose
        # unexpected API response formats.
        preview = json.dumps(data, ensure_ascii=False)[:1500]

        raise RuntimeError(
            "The API request completed, but no text was "
            f"extracted. Response preview: {preview}"
        )

    output_path = Path("ai_explanation.md")
    output_path.write_text(
        explanation + "\n",
        encoding="utf-8",
    )

    return explanation, output_path


def main():
    """Run the prototype from the command line."""

    report_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "quality_report.json"
    )

    print("\n=== SWYNEX AI DATA QUALITY EXPLANATION ===\n")

    try:
        explanation, output_path = explain_report(report_path)

        print(explanation)
        print(f"\nSaved explanation to: {output_path.resolve()}")

    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"\nAI integration error: {error}", file=sys.stderr)
        sys.exit(1)

    except requests.RequestException as error:
        print(
            f"\nNetwork error while contacting Gemini: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
