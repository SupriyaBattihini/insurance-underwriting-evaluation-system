-- SQLite schema for the synthetic insurance underwriting project.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Applicant (
    applicant_id TEXT PRIMARY KEY,
    age INTEGER NOT NULL CHECK (age BETWEEN 18 AND 120),
    region TEXT NOT NULL,
    customer_status TEXT NOT NULL CHECK (customer_status IN ('ACTIVE','INACTIVE'))
);

CREATE TABLE IF NOT EXISTS InsuredAsset (
    asset_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL REFERENCES Applicant(applicant_id),
    asset_type TEXT NOT NULL,
    asset_value REAL NOT NULL CHECK (asset_value > 0),
    risk_data_complete INTEGER NOT NULL CHECK (risk_data_complete IN (0,1))
);

CREATE TABLE IF NOT EXISTS Product (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    base_rate REAL NOT NULL CHECK (base_rate > 0),
    max_coverage REAL NOT NULL CHECK (max_coverage > 0),
    min_age INTEGER NOT NULL,
    max_age INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS CoverageOption (
    coverage_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    coverage_name TEXT NOT NULL,
    min_limit REAL NOT NULL,
    max_limit REAL NOT NULL,
    effective_from TEXT NOT NULL,
    CHECK (min_limit > 0 AND max_limit >= min_limit)
);

CREATE TABLE IF NOT EXISTS RiskFactor (
    risk_factor_id TEXT PRIMARY KEY,
    factor_name TEXT NOT NULL UNIQUE,
    premium_multiplier REAL NOT NULL CHECK (premium_multiplier > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT
);

CREATE TABLE IF NOT EXISTS Quote (
    quote_id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL REFERENCES Applicant(applicant_id),
    asset_id TEXT NOT NULL REFERENCES InsuredAsset(asset_id),
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    requested_coverage REAL NOT NULL CHECK (requested_coverage > 0),
    calculated_premium REAL,
    decision TEXT NOT NULL,
    quote_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Policy (
    policy_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL UNIQUE REFERENCES Quote(quote_id),
    applicant_id TEXT NOT NULL REFERENCES Applicant(applicant_id),
    asset_id TEXT NOT NULL REFERENCES InsuredAsset(asset_id),
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL,
    premium REAL NOT NULL CHECK (premium >= 0),
    accepted INTEGER NOT NULL CHECK (accepted IN (0,1)),
    payment_confirmed INTEGER NOT NULL CHECK (payment_confirmed IN (0,1)),
    CHECK (start_date < end_date)
);

CREATE TABLE IF NOT EXISTS UnderwritingDecision (
    decision_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES Quote(quote_id),
    decision TEXT NOT NULL,
    reason_codes TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Endorsement (
    endorsement_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES Policy(policy_id),
    effective_date TEXT NOT NULL,
    coverage_before REAL NOT NULL,
    coverage_after REAL NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Renewal (
    renewal_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES Policy(policy_id),
    offer_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    status TEXT NOT NULL,
    offered_premium REAL NOT NULL CHECK (offered_premium >= 0)
);

CREATE TABLE IF NOT EXISTS PolicyEvent (
    event_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES Policy(policy_id),
    event_type TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS ProductRiskFactor (
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    risk_factor_id TEXT NOT NULL REFERENCES RiskFactor(risk_factor_id),
    PRIMARY KEY (product_id, risk_factor_id)
);
