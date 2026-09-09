import unittest

from reports.prioritization import value_to_fix_components
from reports.report_intelligence import (
    compare_snapshots,
    is_issue,
    normalize_status,
    rollup_status,
    status_counts,
)


class StatusSemanticsTests(unittest.TestCase):
    def test_distinct_statuses(self):
        self.assertEqual(normalize_status("PASS"), "PASS")
        self.assertEqual(normalize_status("FAIL"), "FAIL")
        self.assertEqual(normalize_status("PARTIAL"), "PARTIAL")
        self.assertEqual(normalize_status("MANUAL_REVIEW"), "MANUAL_REVIEW")
        self.assertEqual(normalize_status("NOT_APPLICABLE"), "NOT_APPLICABLE")
        self.assertEqual(normalize_status("DATA_UNAVAILABLE"), "DATA_UNAVAILABLE")
        self.assertEqual(normalize_status("UNKNOWN"), "DATA_UNAVAILABLE")

    def test_only_fail_partial_are_issues(self):
        self.assertTrue(is_issue("FAIL"))
        self.assertTrue(is_issue("PARTIAL"))
        for status in ("PASS", "MANUAL_REVIEW", "NOT_APPLICABLE", "DATA_UNAVAILABLE"):
            self.assertFalse(is_issue(status), status)

    def test_counts_exclude_review_and_na(self):
        checks = [
            {"status": "FAIL"},
            {"status": "PARTIAL"},
            {"status": "MANUAL_REVIEW"},
            {"status": "NOT_APPLICABLE"},
            {"status": "DATA_UNAVAILABLE"},
            {"status": "PASS"},
        ]
        counts = status_counts(checks)
        self.assertEqual(counts["confirmed_issues"], 2)
        self.assertEqual(counts["review_required"], 1)
        self.assertEqual(counts["not_applicable"], 1)
        self.assertEqual(counts["data_unavailable"], 1)

    def test_rollup_does_not_make_review_a_failure(self):
        self.assertEqual(rollup_status(["PASS", "MANUAL_REVIEW"]), "MANUAL_REVIEW")
        self.assertEqual(rollup_status(["PASS", "DATA_UNAVAILABLE"]), "DATA_UNAVAILABLE")
        self.assertEqual(rollup_status(["PASS", "NOT_APPLICABLE"]), "PASS")


class ScoringTests(unittest.TestCase):
    def test_manual_review_has_no_defect_score(self):
        result = value_to_fix_components(
            {"status": "MANUAL_REVIEW", "severity": "CRITICAL", "pages_affected": 10, "pages_tested": 10, "details": []},
            {},
        )
        self.assertEqual(result["score"], 0.0)

    def test_missing_traffic_is_explicit(self):
        result = value_to_fix_components(
            {"status": "FAIL", "severity": "HIGH", "pages_affected": 5, "pages_tested": 10, "details": []},
            {},
        )
        self.assertTrue(result["partial_inputs"])
        self.assertFalse(result["traffic_available"])


class ComparisonTests(unittest.TestCase):
    def _snapshot(self, status):
        return {
            "audit_signals": [
                {
                    "title": "One clear H1",
                    "path": "/",
                    "observed_status": status,
                    "severity": "HIGH",
                }
            ]
        }

    def test_resolved(self):
        result = compare_snapshots(self._snapshot("PASS"), self._snapshot("FAIL"))
        self.assertEqual(result["page_changes"][0]["change"], "resolved")

    def test_worsened(self):
        result = compare_snapshots(self._snapshot("FAIL"), self._snapshot("PASS"))
        self.assertEqual(result["page_changes"][0]["change"], "worsened")

    def test_unavailable_is_not_comparable(self):
        result = compare_snapshots(self._snapshot("DATA_UNAVAILABLE"), self._snapshot("FAIL"))
        self.assertEqual(result["page_changes"][0]["change"], "not_comparable")

    def test_no_longer_applicable(self):
        result = compare_snapshots(self._snapshot("NOT_APPLICABLE"), self._snapshot("FAIL"))
        self.assertEqual(result["page_changes"][0]["change"], "no_longer_applicable")


if __name__ == "__main__":
    unittest.main()
