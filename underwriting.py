"""Transparent, deterministic rules for the synthetic underwriting demo."""
from decimal import Decimal, ROUND_HALF_UP

PRODUCTS = {
    "Motor Insurance": {"base_rate": 0.020, "max_coverage": 2_000_000, "min_age": 18, "max_age": 85},
    "Property Insurance": {"base_rate": 0.010, "max_coverage": 10_000_000, "min_age": 18, "max_age": 100},
    "Personal Accident Insurance": {"base_rate": 0.005, "max_coverage": 5_000_000, "min_age": 18, "max_age": 70},
}
RISK_MULTIPLIERS = {"Low": 1.0, "Medium": 1.5, "High": 2.5}

def calculate_premium(coverage, product_name, risk_level):
    """Premium = coverage * product base rate * risk multiplier; rounded to paise."""
    if product_name not in PRODUCTS:
        raise ValueError("Unknown product")
    if risk_level not in RISK_MULTIPLIERS:
        raise ValueError("Unknown risk level")
    if coverage <= 0 or coverage > PRODUCTS[product_name]["max_coverage"]:
        raise ValueError("Coverage is outside the product's allowed range")
    value = Decimal(str(coverage)) * Decimal(str(PRODUCTS[product_name]["base_rate"])) * Decimal(str(RISK_MULTIPLIERS[risk_level]))
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def evaluate_quote(age, asset_value, coverage, product_name, risk_level, risk_data_complete=True):
    """Return a decision and reason codes using documented demo rules."""
    reasons = []
    product = PRODUCTS.get(product_name)
    if not product:
        return {"decision": "DECLINED", "reason_codes": ["UNKNOWN_PRODUCT"], "premium": None}
    if age < product["min_age"] or age > product["max_age"]:
        return {"decision": "DECLINED", "reason_codes": ["AGE_INELIGIBLE"], "premium": None}
    if asset_value <= 0:
        return {"decision": "DECLINED", "reason_codes": ["INVALID_ASSET_VALUE"], "premium": None}
    if coverage <= 0 or coverage > product["max_coverage"]:
        return {"decision": "DECLINED", "reason_codes": ["COVERAGE_OUT_OF_PRODUCT_LIMIT"], "premium": None}
    if coverage > asset_value and product_name != "Personal Accident Insurance":
        return {"decision": "DECLINED", "reason_codes": ["COVERAGE_EXCEEDS_ASSET_VALUE"], "premium": None}
    if not risk_data_complete:
        return {"decision": "REFERRED", "reason_codes": ["MISSING_RISK_DATA"], "premium": None}
    if risk_level == "High":
        return {"decision": "REFERRED", "reason_codes": ["HIGH_RISK_REVIEW_REQUIRED"], "premium": calculate_premium(coverage, product_name, risk_level)}
    premium = calculate_premium(coverage, product_name, risk_level)
    return {"decision": "APPROVED", "reason_codes": ["RULES_PASSED"], "premium": premium}

def may_issue_policy(decision, accepted, payment_confirmed, approval_authorized=True):
    return decision == "APPROVED" and accepted and payment_confirmed and approval_authorized
