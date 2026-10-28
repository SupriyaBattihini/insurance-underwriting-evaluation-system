"""Streamlit dashboard for the Insurance Underwriting Evaluation System."""
from pathlib import Path
import subprocess
import sys
import pandas as pd
import streamlit as st
from underwriting import PRODUCTS, evaluate_quote, may_issue_policy

st.set_page_config(page_title="Insurance Underwriting System", page_icon="🛡️", layout="wide")
st.title("🛡️ Insurance Underwriting Evaluation System")
st.caption("Synthetic demonstration project — not for real insurance decisions.")

data_dir = Path("data")
with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose a page", ["Quote Evaluation", "Dataset Dashboard", "Anomaly Report"])
    st.divider()
    st.caption("Rule version: 1.0 | Fixed seed: 20261022")

if page == "Quote Evaluation":
    st.subheader("Evaluate a quote")
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("Applicant age", min_value=1, max_value=120, value=30)
        product_name = st.selectbox("Product", list(PRODUCTS.keys()))
        asset_value = st.number_input("Asset value (₹)", min_value=1, value=500000, step=10000)
    with c2:
        coverage = st.number_input("Requested coverage (₹)", min_value=1, value=300000, step=10000)
        risk_level = st.selectbox("Risk level", ["Low", "Medium", "High"])
        risk_complete = st.checkbox("Required risk data available", value=True)
        accepted = st.checkbox("Customer acceptance recorded")
        payment = st.checkbox("Payment confirmed")
        authorized = st.checkbox("Required approval authority confirmed", value=True)

    if st.button("Evaluate quote", type="primary"):
        result = evaluate_quote(age, asset_value, coverage, product_name, risk_level, risk_complete)
        st.write("**Decision:**", result["decision"])
        st.write("**Reason codes:**", ", ".join(result["reason_codes"]))
        if result["premium"] is not None:
            st.metric("Calculated premium", f"₹{result['premium']:,.2f}")
        issued = may_issue_policy(result["decision"], accepted, payment, authorized)
        if issued:
            st.success("Issuance conditions satisfied in this demonstration. No policy is persisted by this form.")
        else:
            st.info("Policy not issued. Approval, customer acceptance, payment and authorization are all required.")

elif page == "Dataset Dashboard":
    st.subheader("Generated dataset summary")
    if not (data_dir / "applicants.csv").exists():
        st.warning("No dataset found yet. Run `python generate_data.py` in the project terminal.")
    else:
        files = ["applicants.csv", "insured_assets.csv", "quotes.csv", "policies.csv",
                 "endorsements.csv", "renewals.csv", "underwriting_decisions.csv"]
        cols = st.columns(4)
        for col, name in zip(cols, files[:4]):
            df = pd.read_csv(data_dir / name)
            col.metric(name.replace(".csv", "").replace("_", " ").title(), f"{len(df):,}")
        selected = st.selectbox("Preview dataset", files)
        st.dataframe(pd.read_csv(data_dir / selected).head(100), use_container_width=True)

elif page == "Anomaly Report":
    st.subheader("Validation and anomaly report")
    report_path = data_dir / "validation_summary.json"
    issues_path = data_dir / "detected_issues.csv"
    if not report_path.exists():
        st.warning("Run `python validate_data.py` in the project terminal after generating data.")
    else:
        import json
        report = json.loads(report_path.read_text())
        st.metric("Detected issue records", report["issue_count"])
        st.write("**Status:**", report["status"])
        st.json(report["row_counts"])
        if issues_path.exists():
            st.dataframe(pd.read_csv(issues_path), use_container_width=True)
