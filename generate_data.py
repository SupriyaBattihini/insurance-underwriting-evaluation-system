"""Generate reproducible synthetic insurance data. No real customer data is used."""
from pathlib import Path
import json
import random
import hashlib
import pandas as pd
from underwriting import PRODUCTS, RISK_MULTIPLIERS, calculate_premium, evaluate_quote, may_issue_policy

SEED = 20261022
OUT = Path("data")
OUT.mkdir(exist_ok=True)

def make_id(prefix, n):
    return f"{prefix}-2026-{n:06d}"

def generate():
    random.seed(SEED)
    rng = random.Random(SEED)
    product_names = list(PRODUCTS)

    applicants = []
    for i in range(1, 3001):
        applicants.append({
            "applicant_id": make_id("APP", i),
            "age": rng.randint(18, 80),
            "region": rng.choice(["North", "South", "East", "West", "Central"]),
            "customer_status": "ACTIVE",
        })
    applicant_df = pd.DataFrame(applicants)

    assets = []
    for i in range(1, 3001):
        applicant = applicants[i-1]
        assets.append({
            "asset_id": f"AST-2026-{i:06d}",
            "applicant_id": applicant["applicant_id"],
            "asset_type": rng.choice(["Vehicle", "Property", "Personal"]),
            "asset_value": rng.randint(100000, 1500000),
            "risk_data_complete": rng.random() > 0.06,
        })
    asset_df = pd.DataFrame(assets)

    products = []
    coverage_options = []
    risk_factors = []
    for i, (name, rule) in enumerate(PRODUCTS.items(), 1):
        products.append({
            "product_id": f"PRD-{i:03d}", "product_name": name,
            "base_rate": rule["base_rate"], "max_coverage": rule["max_coverage"],
            "min_age": rule["min_age"], "max_age": rule["max_age"],
            "effective_from": "2026-01-01", "status": "ACTIVE"
        })
        coverage_options.append({
            "coverage_id": f"COV-{i:03d}", "product_id": f"PRD-{i:03d}",
            "coverage_name": "Standard", "min_limit": 1000,
            "max_limit": rule["max_coverage"], "effective_from": "2026-01-01"
        })
    for i, (name, multiplier) in enumerate(RISK_MULTIPLIERS.items(), 1):
        risk_factors.append({
            "risk_factor_id": f"RSK-{i:03d}", "factor_name": name,
            "premium_multiplier": multiplier, "effective_from": "2026-01-01",
            "effective_to": ""
        })

    quotes = []
    decisions = []
    # 4,000 quote records. Decisions are generated from rules, not random labels.
    for i in range(1, 4001):
        app = applicants[(i - 1) % len(applicants)]
        asset = assets[(i * 7 - 1) % len(assets)]
        product_name = product_names[(i - 1) % len(product_names)]
        rule = PRODUCTS[product_name]
        risk_level = rng.choices(["Low", "Medium", "High"], weights=[0.60, 0.30, 0.10])[0]
        coverage = min(rng.randint(50000, 500000), rule["max_coverage"])
        asset_value = asset["asset_value"]
        if product_name == "Personal Accident Insurance":
            # Personal accident cover is not tied to asset value.
            asset_value = max(asset_value, coverage)
        complete = bool(asset["risk_data_complete"])
        result = evaluate_quote(app["age"], asset_value, coverage, product_name, risk_level, complete)
        accepted = result["decision"] == "APPROVED" and (i % 5 != 0)
        payment = accepted and (i % 7 != 0)
        issued = may_issue_policy(result["decision"], accepted, payment)
        qid = make_id("QTE", i)
        quotes.append({
            "quote_id": qid, "applicant_id": app["applicant_id"], "asset_id": asset["asset_id"],
            "product_id": f"PRD-{product_names.index(product_name)+1:03d}",
            "product_name": product_name, "quote_date": f"2026-{((i-1)%12)+1:02d}-15",
            "requested_coverage": coverage, "risk_level": risk_level,
            "risk_data_complete": complete, "calculated_premium": result["premium"],
            "decision": result["decision"], "reason_codes": "|".join(result["reason_codes"]),
            "customer_accepted": accepted, "payment_confirmed": payment,
            "policy_issued": issued, "status": "ISSUED" if issued else result["decision"]
        })
        decisions.append({
            "decision_id": f"DEC-2026-{i:06d}", "quote_id": qid,
            "decision": result["decision"], "reason_codes": "|".join(result["reason_codes"]),
            "approver_id": "SYS-RULES" if result["decision"] == "APPROVED" else "UW-REVIEW",
            "rule_version": "1.0", "created_at": f"2026-{((i-1)%12)+1:02d}-16"
        })

    # Exactly 2,000 policy rows, linked to the first 2,000 quote IDs.
    # Valid policy records are created from quotes that meet issuance conditions;
    # if necessary, use the next valid eligible quotes until the target is met.
    issued_quotes = [q for q in quotes if q["policy_issued"]]
    # Make the baseline count exactly 2,000 with a controlled synthetic business scenario:
    # select eligible approved quotes and mark acceptance/payment true before creating policy.
    policy_source = []
    for q in quotes:
        if q["decision"] == "APPROVED" and q["calculated_premium"] is not None:
            policy_source.append(q)
        if len(policy_source) == 2000:
            break
    policies = []
    for n, q in enumerate(policy_source, 1):
        q["customer_accepted"] = True
        q["payment_confirmed"] = True
        q["policy_issued"] = True
        q["status"] = "ISSUED"
        policies.append({
            "policy_id": f"POL-2026-{n:06d}", "quote_id": q["quote_id"],
            "applicant_id": q["applicant_id"], "asset_id": q["asset_id"],
            "product_id": q["product_id"], "start_date": "2026-01-01",
            "end_date": "2026-12-31", "status": "ISSUED",
            "premium": q["calculated_premium"], "accepted": True, "payment_confirmed": True
        })

    # Add a cancelled policy while preserving its record.
    if policies:
        policies[-1]["status"] = "CANCELLED"
        policies[-1]["cancellation_date"] = "2026-06-30"

    endorsements = []
    for n, p in enumerate(policies[:250], 1):
        endorsements.append({
            "endorsement_id": f"END-{p['policy_id']}-{n:03d}",
            "policy_id": p["policy_id"], "effective_date": "2026-07-01",
            "coverage_before": 100000, "coverage_after": 110000,
            "status": "APPROVED", "issue_type": ""
        })

    renewals = []
    for n, p in enumerate(policies[:1200], 1):
        renewals.append({
            "renewal_id": f"REN-{p['policy_id']}-2027",
            "policy_id": p["policy_id"], "offer_date": "2026-11-01",
            "expiry_date": "2026-12-31",
            "status": "DECLINED" if n % 5 == 0 else ("ACCEPTED" if n % 3 == 0 else "PENDING"),
            "offered_premium": round(float(p["premium"]) * 1.05, 2)
        })

    # Deliberately labelled anomalies. These are test cases, not hidden input labels.
    ground_truth = [
        {"record_id": "POL-2026-000001", "entity_type": "Policy", "issue_type": "POLICY_WITHOUT_ACCEPTANCE", "expected_result": "FLAG"},
        {"record_id": "QTE-2026-000002", "entity_type": "Quote", "issue_type": "PREMIUM_MISMATCH", "expected_result": "FLAG"},
        {"record_id": "END-POL-2026-000001-001", "entity_type": "Endorsement", "issue_type": "ENDORSEMENT_LIMIT_EXCEEDED", "expected_result": "FLAG"},
        {"record_id": "REN-POL-2026-000200-2027", "entity_type": "Renewal", "issue_type": "RENEWAL_FOR_CANCELLED_POLICY", "expected_result": "FLAG"},
        {"record_id": "POL-2026-000001", "entity_type": "Policy", "issue_type": "UNPERMITTED_POLICY_OVERLAP", "expected_result": "FLAG"},
    ]

    # Inject only the specific anomalies that the validation module can reproduce.
    policies[0]["accepted"] = False
    quotes[1]["calculated_premium"] = float(quotes[1]["calculated_premium"] or 0) + 123.45
    if endorsements:
        endorsements[0]["coverage_after"] = PRODUCTS[quotes[0]["product_name"]]["max_coverage"] + 1
        endorsements[0]["status"] = "APPROVED"
    if len(policies) >= 200:
        policies[199]["status"] = "CANCELLED"
        policies[199]["cancellation_date"] = "2026-06-01"

    # Create a separate second policy period for overlap anomaly, preserving policy history.
    if policies:
        overlap = dict(policies[0])
        overlap["policy_id"] = "POL-2026-002001"
        overlap["start_date"] = "2026-06-01"
        overlap["end_date"] = "2027-05-31"
        overlap["status"] = "ISSUED"
        policies.append(overlap)

    tables = {
        "applicants.csv": applicant_df,
        "insured_assets.csv": asset_df,
        "products.csv": pd.DataFrame(products),
        "coverage_options.csv": pd.DataFrame(coverage_options),
        "risk_factors.csv": pd.DataFrame(risk_factors),
        "quotes.csv": pd.DataFrame(quotes),
        "policies.csv": pd.DataFrame(policies),
        "underwriting_decisions.csv": pd.DataFrame(decisions),
        "endorsements.csv": pd.DataFrame(endorsements),
        "renewals.csv": pd.DataFrame(renewals),
        "ground_truth.csv": pd.DataFrame(ground_truth),
    }
    for filename, df in tables.items():
        df.to_csv(OUT / filename, index=False)

    manifest = {
        "project": "Insurance Underwriting Evaluation System",
        "seed": SEED,
        "generator_version": "1.0",
        "data_type": "synthetic",
        "source_manifest": "No external personal data used",
        "row_counts": {name: int(len(df)) for name, df in tables.items()},
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Generated files in data/")
    print(json.dumps(manifest["row_counts"], indent=2))

if __name__ == "__main__":
    generate()
