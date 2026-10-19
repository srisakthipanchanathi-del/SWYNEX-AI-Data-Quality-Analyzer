"""SWYNEX interactive data-quality analyzer."""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import analyze_csv
from ai_explainer import explain_report
from evaluate import evaluate_dataset


st.set_page_config(
    page_title="SWYNEX | AI Data Quality",
    page_icon="🔎",
    layout="wide",
)

st.title("SWYNEX")
st.subheader("AI-Powered Data Quality Analyzer")
st.write(
    "Upload a CSV to detect missing values, duplicate records, "
    "and potential numeric outliers. Review the findings before "
    "changing any data."
)

with st.sidebar:
    st.header("Evaluation")
    st.write("Evaluate detections against the labelled sample dataset.")
    run_eval = st.button("Run evaluation", use_container_width=True)

uploaded = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)

        if df.empty:
            st.error("This CSV contains no data rows.")
            st.stop()

        if len(df.columns) == 0:
            st.error("This CSV contains no columns.")
            st.stop()

        st.markdown("### Data preview")
        st.dataframe(df.head(20), use_container_width=True)

        if st.button("Analyze data", type="primary"):
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".csv", delete=False
            ) as tmp:
                tmp.write(uploaded.getvalue())
                temp_path = tmp.name

            try:
                with st.spinner("Analyzing your dataset..."):
                    report = analyze_csv(temp_path)

                st.session_state["swynex_report"] = report
                st.success("Analysis completed.")
            finally:
                Path(temp_path).unlink(missing_ok=True)

    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        st.error(f"Unable to read this CSV: {exc}")
    except Exception as exc:
        st.error(f"Analysis failed safely: {exc}")

report = st.session_state.get("swynex_report")

if report:
    st.markdown("### Data quality results")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", report["rows"])
    c2.metric("Columns", report["columns"])
    c3.metric("Missing cells", report["missing_cells"])
    c4.metric("Duplicate rows", report["duplicate_rows"])

    st.metric(
        "Data quality score",
        f'{report["quality_score"]}/100',
        help=report.get("score_note", ""),
    )

    st.caption(
        f'Potential outlier rows: {report["potential_outlier_rows"]}. '
        "Outliers are candidates for review, not confirmed errors."
    )

    with st.expander("Missing values by column", expanded=True):
        missing = pd.DataFrame(
            list(report["missing_by_column"].items()),
            columns=["Column", "Missing values"],
        )
        st.dataframe(missing, use_container_width=True, hide_index=True)

    with st.expander("Full analysis report"):
        st.json(report)

    st.markdown("### AI explanation")
    if st.button("Generate AI recommendations"):
        if not os.getenv("GEMINI_API_KEY"):
            st.warning(
                "GEMINI_API_KEY is not configured. The analysis works "
                "without AI; configure the key to generate recommendations."
            )
        else:
            try:
                with st.spinner("Requesting AI explanation..."):
                    # The analyzer writes quality_report.json.
                    explanation, output_path = explain_report(
                        "quality_report.json"
                    )
                st.session_state["swynex_explanation"] = explanation
                st.success(f"Explanation saved to {output_path}")
            except Exception as exc:
                st.error(
                    "The AI explanation could not be generated. "
                    "Check the API key, network connection, and model/API "
                    f"configuration. Details: {exc}"
                )

    explanation = st.session_state.get("swynex_explanation")
    if explanation:
        st.markdown(explanation)

    st.download_button(
        "Download analysis report",
        data=json.dumps(report, indent=2, default=str),
        file_name="quality_report.json",
        mime="application/json",
    )

if run_eval:
    try:
        with st.spinner("Evaluating labelled sample data..."):
            results = evaluate_dataset()
        st.markdown("### Evaluation results")
        st.write(f'Records evaluated: {results["records_evaluated"]}')
        st.dataframe(
            pd.DataFrame(results["results"]).T,
            use_container_width=True,
        )
        st.info("Interpret results in the context of the synthetic labels.")
        st.json({"limitations": results["limitations"]})
    except Exception as exc:
        st.error(f"Evaluation failed: {exc}")

st.divider()
st.caption(
    "SWYNEX is a prototype. Validate flagged records before deleting, "
    "imputing, or modifying data. The quality score is a project-defined "
    "heuristic, not an industry-standard metric."
)
