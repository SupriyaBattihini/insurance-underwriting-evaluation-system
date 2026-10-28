import unittest
from underwriting import calculate_premium, evaluate_quote, may_issue_policy

class UnderwritingTests(unittest.TestCase):
    def test_premium_is_deterministic(self):
        self.assertEqual(calculate_premium(100000, "Motor Insurance", "Low"), 2000.0)
        self.assertEqual(calculate_premium(100000, "Motor Insurance", "Low"), 2000.0)

    def test_high_risk_is_referred(self):
        result = evaluate_quote(30, 500000, 100000, "Motor Insurance", "High", True)
        self.assertEqual(result["decision"], "REFERRED")

    def test_missing_risk_data_is_referred(self):
        result = evaluate_quote(30, 500000, 100000, "Motor Insurance", "Low", False)
        self.assertEqual(result["decision"], "REFERRED")
        self.assertIn("MISSING_RISK_DATA", result["reason_codes"])

    def test_age_ineligible_declined(self):
        result = evaluate_quote(16, 500000, 100000, "Motor Insurance", "Low", True)
        self.assertEqual(result["decision"], "DECLINED")

    def test_policy_issue_gate(self):
        self.assertTrue(may_issue_policy("APPROVED", True, True, True))
        self.assertFalse(may_issue_policy("APPROVED", True, False, True))
        self.assertFalse(may_issue_policy("REFERRED", True, True, True))

if __name__ == "__main__":
    unittest.main()
