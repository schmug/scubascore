"""Tests for data models."""

import unittest
from datetime import datetime

from scubascore.models import (
    Rule, Verdict, ServiceScore, DataQuality, ScoreResult,
    WeightConfig, ServiceWeightConfig, CompensatingControlConfig
)


class TestRule(unittest.TestCase):
    """Test Rule model."""
    
    def test_rule_creation(self):
        """Test creating a rule."""
        rule = Rule(
            rule_id="gws.gmail.1.1",
            verdict=Verdict.PASS,
            service="gmail",
            weight=5.0
        )
        self.assertEqual(rule.rule_id, "gws.gmail.1.1")
        self.assertEqual(rule.verdict, Verdict.PASS)
        self.assertEqual(rule.service, "gmail")
        self.assertEqual(rule.weight, 5.0)
    
    def test_is_evaluated(self):
        """Test is_evaluated method."""
        # Pass and Fail are evaluated
        rule = Rule("test", Verdict.PASS)
        self.assertTrue(rule.is_evaluated())
        
        rule = Rule("test", Verdict.FAIL)
        self.assertTrue(rule.is_evaluated())
        
        # Others are not
        rule = Rule("test", Verdict.NA)
        self.assertFalse(rule.is_evaluated())
        
        rule = Rule("test", Verdict.UNKNOWN)
        self.assertFalse(rule.is_evaluated())
    
    def test_score_contribution(self):
        """Test score contribution calculation."""
        # Passed rule contributes full weight
        rule = Rule("test", Verdict.PASS, weight=5.0)
        self.assertEqual(rule.get_score_contribution(), 5.0)
        
        # Failed rule contributes 0
        rule = Rule("test", Verdict.FAIL, weight=5.0)
        self.assertEqual(rule.get_score_contribution(), 0.0)
        
        # Failed rule with compensating control contributes 50%
        rule = Rule("test", Verdict.FAIL, weight=5.0, compensating_control="mitigation")
        self.assertEqual(rule.get_score_contribution(), 2.5)
        
        # Non-evaluated rules contribute 0
        rule = Rule("test", Verdict.NA, weight=5.0)
        self.assertEqual(rule.get_score_contribution(), 0.0)


class TestServiceScore(unittest.TestCase):
    """Test ServiceScore model."""
    
    def test_service_score_creation(self):
        """Test creating a service score."""
        score = ServiceScore(
            service_name="gmail",
            evaluated_weight=10.0,
            passed_weight=8.0,
            passed_rules=[("rule1", 5.0), ("rule2", 3.0)],
            failed_rules=[("rule3", 2.0, False)]
        )
        self.assertEqual(score.service_name, "gmail")
        self.assertEqual(score.passed_count, 2)
        self.assertEqual(score.failed_count, 1)
    
    def test_calculate_score(self):
        """Test score calculation."""
        score = ServiceScore(
            service_name="gmail",
            evaluated_weight=10.0,
            passed_weight=8.0
        )
        score.calculate_score()
        self.assertEqual(score.score, 80.0)
        
        # Test with no evaluated weight
        score = ServiceScore("test", evaluated_weight=0.0)
        score.calculate_score()
        self.assertIsNone(score.score)


class TestWeightConfig(unittest.TestCase):
    """Test WeightConfig model."""
    
    def test_exact_match(self):
        """Test exact rule ID matching."""
        config = WeightConfig(weights={
            "gws.gmail.1.1": 5.0,
            "gws.drive.2.1": 3.0
        })
        self.assertEqual(config.get_weight("gws.gmail.1.1"), 5.0)
        self.assertEqual(config.get_weight("gws.drive.2.1"), 3.0)
    
    def test_prefix_match(self):
        """Test prefix-based matching."""
        config = WeightConfig(weights={
            "gws.gmail.": 3.0,
            "gws.": 2.0
        })
        # Longest prefix wins
        self.assertEqual(config.get_weight("gws.gmail.1.1"), 3.0)
        self.assertEqual(config.get_weight("gws.drive.1.1"), 2.0)
        self.assertEqual(config.get_weight("other.rule"), 1.0)  # default
    
    def test_default_weight(self):
        """Test default weight handling."""
        config = WeightConfig()
        self.assertEqual(config.get_weight("any.rule"), 1.0)
        self.assertEqual(config.get_weight("any.rule", default=2.5), 2.5)


class TestDataQuality(unittest.TestCase):
    """Test DataQuality model."""
    
    def test_data_quality(self):
        """Test data quality metrics."""
        dq = DataQuality(
            total_entries=100,
            unknown_entries=5,
            error_entries=3,
            na_entries=10
        )
        self.assertEqual(dq.unknown_or_error_entries, 8)
        self.assertEqual(dq.total_entries, 100)


class TestScoreResult(unittest.TestCase):
    """Test ScoreResult model."""
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        service_score = ServiceScore(
            service_name="gmail",
            score=85.5,
            evaluated_weight=10.0,
            passed_weight=8.55,
            passed_rules=[("rule1", 5.0)],
            failed_rules=[("rule2", 5.0, True)]
        )
        
        result = ScoreResult(
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            overall_score=85.5,
            service_scores={"gmail": service_score},
            data_quality=DataQuality(total_entries=10, unknown_entries=1)
        )
        
        data = result.to_dict()
        self.assertEqual(data["overall_score"], 85.5)
        self.assertEqual(data["per_service"]["gmail"]["score"], 85.5)
        self.assertEqual(data["data_quality"]["total_entries_seen"], 10)
        self.assertTrue(data["generated_at"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()