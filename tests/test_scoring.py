"""Tests for scoring module."""

import unittest
from datetime import datetime

from scubascore.models import Rule, Verdict, ServiceWeightConfig
from scubascore.scoring import (
    compute_scores, calculate_overall_score, get_failed_rules_by_severity,
    get_score_summary
)


class TestComputeScores(unittest.TestCase):
    """Test score computation."""
    
    def test_empty_rules(self):
        """Test scoring with no rules."""
        result = compute_scores([])
        self.assertIsNone(result.overall_score)
        self.assertEqual(len(result.service_scores), 0)
        self.assertEqual(result.data_quality.total_entries, 0)
    
    def test_single_service_all_pass(self):
        """Test scoring with all passing rules."""
        rules = [
            Rule("rule1", Verdict.PASS, service="gmail", weight=5.0),
            Rule("rule2", Verdict.PASS, service="gmail", weight=3.0),
        ]
        
        result = compute_scores(rules)
        self.assertEqual(len(result.service_scores), 1)
        self.assertEqual(result.service_scores["gmail"].score, 100.0)
        self.assertEqual(result.service_scores["gmail"].evaluated_weight, 8.0)
        self.assertEqual(result.service_scores["gmail"].passed_weight, 8.0)
    
    def test_single_service_mixed(self):
        """Test scoring with mixed pass/fail rules."""
        rules = [
            Rule("rule1", Verdict.PASS, service="gmail", weight=5.0),
            Rule("rule2", Verdict.FAIL, service="gmail", weight=5.0),
        ]
        
        result = compute_scores(rules)
        self.assertEqual(result.service_scores["gmail"].score, 50.0)
        self.assertEqual(result.service_scores["gmail"].passed_count, 1)
        self.assertEqual(result.service_scores["gmail"].failed_count, 1)
    
    def test_compensating_control(self):
        """Test scoring with compensating controls."""
        rules = [
            Rule("rule1", Verdict.PASS, service="gmail", weight=5.0),
            Rule("rule2", Verdict.FAIL, service="gmail", weight=5.0, 
                 compensating_control="Alternative implementation"),
        ]
        
        result = compute_scores(rules)
        # Should get 50% credit for compensating control
        self.assertEqual(result.service_scores["gmail"].score, 75.0)
        self.assertEqual(result.service_scores["gmail"].passed_weight, 7.5)
    
    def test_multiple_services(self):
        """Test scoring with multiple services."""
        rules = [
            Rule("rule1", Verdict.PASS, service="gmail", weight=5.0),
            Rule("rule2", Verdict.FAIL, service="gmail", weight=5.0),
            Rule("rule3", Verdict.PASS, service="drive", weight=3.0),
            Rule("rule4", Verdict.PASS, service="drive", weight=2.0),
        ]
        
        result = compute_scores(rules)
        self.assertEqual(len(result.service_scores), 2)
        self.assertEqual(result.service_scores["gmail"].score, 50.0)
        self.assertEqual(result.service_scores["drive"].score, 100.0)
    
    def test_unspecified_service(self):
        """Test rules without service specified."""
        rules = [
            Rule("rule1", Verdict.PASS, service=None, weight=5.0),
            Rule("rule2", Verdict.FAIL, service=None, weight=3.0),
        ]
        
        result = compute_scores(rules)
        self.assertIn("unspecified", result.service_scores)
        self.assertEqual(result.service_scores["unspecified"].score, 62.5)
    
    def test_non_evaluated_verdicts(self):
        """Test handling of non-evaluated verdicts."""
        rules = [
            Rule("rule1", Verdict.PASS, service="gmail", weight=5.0),
            Rule("rule2", Verdict.NA, service="gmail", weight=3.0),
            Rule("rule3", Verdict.UNKNOWN, service="gmail", weight=2.0),
            Rule("rule4", Verdict.ERROR, service="gmail", weight=1.0),
        ]
        
        result = compute_scores(rules)
        # Only PASS rule should be evaluated
        self.assertEqual(result.service_scores["gmail"].evaluated_weight, 5.0)
        self.assertEqual(result.service_scores["gmail"].score, 100.0)
        self.assertEqual(result.data_quality.na_entries, 1)
        self.assertEqual(result.data_quality.unknown_entries, 1)
        self.assertEqual(result.data_quality.error_entries, 1)


class TestCalculateOverallScore(unittest.TestCase):
    """Test overall score calculation."""
    
    def test_single_service(self):
        """Test overall score with single service."""
        from scubascore.models import ServiceScore
        
        service_scores = {
            "gmail": ServiceScore("gmail", score=80.0)
        }
        service_weights = ServiceWeightConfig()
        
        overall = calculate_overall_score(service_scores, service_weights)
        self.assertEqual(overall, 80.0)
    
    def test_weighted_average(self):
        """Test weighted average calculation."""
        from scubascore.models import ServiceScore
        
        service_scores = {
            "gmail": ServiceScore("gmail", score=80.0),
            "drive": ServiceScore("drive", score=90.0),
        }
        service_weights = ServiceWeightConfig(service_weights={
            "gmail": 0.6,
            "drive": 0.4
        })
        
        overall = calculate_overall_score(service_scores, service_weights)
        # (80 * 0.6 + 90 * 0.4) / (0.6 + 0.4) = 84.0
        self.assertEqual(overall, 84.0)
    
    def test_missing_service_weight(self):
        """Test handling of services not in weight config."""
        from scubascore.models import ServiceScore
        
        service_scores = {
            "unknown_service": ServiceScore("unknown_service", score=70.0)
        }
        service_weights = ServiceWeightConfig()
        
        overall = calculate_overall_score(service_scores, service_weights)
        # Should use default weight of 0.1
        self.assertEqual(overall, 70.0)
    
    def test_no_scores(self):
        """Test with no service scores."""
        service_scores = {}
        service_weights = ServiceWeightConfig()
        
        overall = calculate_overall_score(service_scores, service_weights)
        self.assertIsNone(overall)


class TestGetFailedRulesBySeverity(unittest.TestCase):
    """Test failed rules grouping by severity."""
    
    def test_severity_grouping(self):
        """Test grouping failed rules by severity."""
        rules = [
            Rule("critical1", Verdict.FAIL, weight=5.0),
            Rule("critical2", Verdict.FAIL, weight=6.0),
            Rule("high1", Verdict.FAIL, weight=3.0),
            Rule("medium1", Verdict.FAIL, weight=2.0),
            Rule("low1", Verdict.FAIL, weight=1.0),
            Rule("pass1", Verdict.PASS, weight=5.0),  # Should not appear
        ]
        
        failed_by_severity = get_failed_rules_by_severity(rules)
        
        self.assertEqual(len(failed_by_severity["Critical"]), 2)
        self.assertEqual(len(failed_by_severity["High"]), 1)
        self.assertEqual(len(failed_by_severity["Medium"]), 1)
        self.assertEqual(len(failed_by_severity["Low"]), 1)
    
    def test_compensating_controls_excluded(self):
        """Test that rules with compensating controls are excluded."""
        rules = [
            Rule("critical1", Verdict.FAIL, weight=5.0),
            Rule("critical2", Verdict.FAIL, weight=5.0, 
                 compensating_control="Mitigation in place"),
        ]
        
        failed_by_severity = get_failed_rules_by_severity(rules)
        
        # Only the rule without compensating control should appear
        self.assertEqual(len(failed_by_severity.get("Critical", [])), 1)
        self.assertEqual(failed_by_severity["Critical"][0].rule_id, "critical1")


class TestGetScoreSummary(unittest.TestCase):
    """Test score summary generation."""
    
    def test_summary_generation(self):
        """Test generating score summary."""
        from scubascore.models import ServiceScore, ScoreResult, DataQuality
        
        result = ScoreResult(
            generated_at=datetime.utcnow(),
            overall_score=85.0,
            service_scores={
                "gmail": ServiceScore(
                    "gmail", score=90.0, 
                    passed_rules=[("r1", 5.0), ("r2", 3.0)],
                    failed_rules=[("r3", 2.0, False)]
                ),
                "drive": ServiceScore(
                    "drive", score=75.0,
                    passed_rules=[("r4", 3.0)],
                    failed_rules=[("r5", 1.0, True)]
                ),
            },
            data_quality=DataQuality(total_entries=10, unknown_entries=1)
        )
        
        summary = get_score_summary(result)
        
        self.assertEqual(summary["overall_score"], 85.0)
        self.assertEqual(summary["services_analyzed"], 2)
        self.assertEqual(summary["services_meeting_80_percent"], 1)  # Only gmail
        self.assertEqual(summary["total_rules_evaluated"], 5)
        self.assertEqual(summary["total_passed"], 3)
        self.assertEqual(summary["total_failed"], 2)
        self.assertEqual(summary["data_quality"]["total_entries"], 10)
        self.assertEqual(summary["data_quality"]["evaluation_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()