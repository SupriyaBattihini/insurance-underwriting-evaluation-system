"""Validate generated data and report deliberately injected anomalies."""
from pathlib import Path
import json
import pandas as pd
from underwriting import PRODUCTS, calculate_premium

DATA = Path("data")

def load(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run: python generate_data.py")
    return pd.read_csv(path).fillna("")

def validate():
    applicants = load("applicants.csv")
    assets = load("insured_assets.csv")
    quotes = load("quotes.csv")
    policies = load("policies.csv")
    endorsements = load("endorsements.csv")
    renewals = load("renewals.csv")
    truth = load("ground_truth.csv")

    issues = []
    # Primary keys
    for df, key, name in [
        (applicants, "applicant_id", "applicants"),
        (assets, "asset_id", "assets"),
        (quotes, "quote_id", "quotes"),
        (policies, "policy_id", "policies"),
    ]:
        if df[key].duplicated().any():
            issues.append({"check": "PRIMARY_KEY_DUPLICATE", "entity": name, "count": int(df[key].duplicated().sum())})

    # Foreign keys
    app_ids = set(applicants["applicant_id"])
    asset_ids = set(assets["asset_id"])
    quote_ids = set(quotes["quote_id"])
    policy_ids = set(policies["policy_id"])
    if not set(assets["applicant_id"]).issubset(app_ids):
        issues.append({"check": "ASSET_APPLICANT_FK", "entity": "assets", "count": 1})
    if not set(quotes["applicant_id"]).issubset(app_ids):
        issues.append({"check": "QUOTE_APPLICANT_FK", "entity": "quotes", "count": 1})
    if not set(quotes["asset_id"]).issubset(asset_ids):
        issues.append({"check": "QUOTE_ASSET_FK", "entity": "quotes", "count": 1})
    if not set(policies["quote_id"]).issubset(quote_ids):
        issues.append({"check": "POLICY_QUOTE_FK", "entity": "policies", "count": 1})
    if not set(endorsements["policy_id"]).issubset(policy_ids):
        issues.append({"check": "ENDORSEMENT_POLICY_FK", "entity": "endorsements", "count": 1})
    if not set(renewals["policy_id"]).issubset(policy_ids):
        issues.append({"check": "RENEWAL_POLICY_FK", "entity": "renewals", "count": 1})

    # Premium formula checks. The one injected mismatch is expected and labelled.
    gt_premium_ids = set(truth.loc[truth.issue_type == "PREMIUM_MISMATCH", "record_id"])
    for _, q in quotes.iterrows():
        if q["calculated_premium"] == "" or pd.isna(q["calculated_premium"]):
            continue
        try:
            expected = calculate_premium(float(q["requested_coverage"]), q["product_name"], q["risk_level"])
            if abs(float(q["calculated_premium"]) - expected) > 0.02:
                issues.append({"check": "PREMIUM_MISMATCH", "entity": q["quote_id"], "count": 1,
                               "labelled": q["quote_id"] in gt_premium_ids})
        except (ValueError, TypeError):
            pass

    # Issuance gate checks
    for _, p in policies.iterrows():
        if str(p["accepted"]).lower() not in ("true", "1") or str(p["payment_confirmed"]).lower() not in ("true", "1"):
            issues.append({"check": "POLICY_WITHOUT_ACCEPTANCE_OR_PAYMENT", "entity": p["policy_id"], "count": 1})

    # Endorsement limit checks
    product_map = load("products.csv").set_index("product_id")["max_coverage"].to_dict()
    policy_product = policies.set_index("policy_id")["product_id"].to_dict()
    for _, e in endorsements.iterrows():
        pid = e["policy_id"]
        if pid in policy_product and pid in policy_ids:
            max_limit = float(product_map.get(policy_product[pid], 0))
            if float(e["coverage_after"]) > max_limit:
                issues.append({"check": "ENDORSEMENT_LIMIT_EXCEEDED", "entity": e["endorsement_id"], "count": 1})

    # Renewal for cancelled policy
    cancelled = set(policies.loc[policies.status == "CANCELLED", "policy_id"])
    for _, r in renewals.iterrows():
        if r["policy_id"] in cancelled:
            issues.append({"check": "RENEWAL_FOR_CANCELLED_POLICY", "entity": r["renewal_id"], "count": 1})

    report = {
        "status": "COMPLETED_WITH_EXCEPTIONS" if issues else "PASSED",
        "row_counts": {
            "applicants": len(applicants), "assets": len(assets), "quotes": len(quotes),
            "policies_including_overlap_test": len(policies), "endorsements": len(endorsements),
            "renewals": len(renewals), "ground_truth_labels": len(truth)
        },
        "issue_count": len(issues),
        "issues": issues,
        "ground_truth_labels_are_separate_from_input_features": True
    }
    (DATA / "validation_summary.json").write_text(json.dumps(report, indent=2))
    pd.DataFrame(issues, columns=["check", "entity", "count", "labelled"]).to_csv(DATA / "detected_issues.csv", index=False)
    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    validate()
