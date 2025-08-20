"""Tests for parsers module."""

import unittest
from unittest.mock import mock_open, patch
import json
import yaml

from scubascore.parsers import (
    normalize_verdict, infer_service_from_rule_id, parse_rule_entry,
    iter_rules_from_json, parse_scuba_results, load_json_flexible,
    load_yaml_config, WeightConfig, Verdict
)
from scubascore.exceptions import ParsingError, ConfigurationError


class TestNormalizeVerdict(unittest.TestCase):
    """Test verdict normalization."""
    
    def test_pass_variants(self):
        """Test PASS verdict variants."""
        for value in ["PASS", "pass", "Passed", "TRUE", "true", "SUCCESS"]:
            self.assertEqual(normalize_verdict(value), Verdict.PASS)
    
    def test_fail_variants(self):
        """Test FAIL verdict variants."""
        for value in ["FAIL", "fail", "Failed", "FALSE", "false", "FAILURE"]:
            self.assertEqual(normalize_verdict(value), Verdict.FAIL)
    
    def test_na_variants(self):
        """Test NA verdict variants."""
        for value in ["N/A", "NA", "n/a", "NOT APPLICABLE", "NOT_APPLICABLE"]:
            self.assertEqual(normalize_verdict(value), Verdict.NA)
    
    def test_unknown_variants(self):
        """Test UNKNOWN verdict variants."""
        for value in ["UNKNOWN", "ERROR", "error", "UNDEFINED", None]:
            self.assertEqual(normalize_verdict(value), Verdict.UNKNOWN)
    
    def test_invalid_verdict(self):
        """Test invalid verdict values."""
        self.assertEqual(normalize_verdict("INVALID"), Verdict.UNKNOWN)
        self.assertEqual(normalize_verdict(""), Verdict.UNKNOWN)


class TestInferService(unittest.TestCase):
    """Test service inference from rule IDs."""
    
    def test_standard_patterns(self):
        """Test standard rule ID patterns."""
        self.assertEqual(infer_service_from_rule_id("gws.gmail.1.1"), "gmail")
        self.assertEqual(infer_service_from_rule_id("gws.drive.2.3"), "drive")
        self.assertEqual(infer_service_from_rule_id("scuba.common.4.5"), "common")
    
    def test_no_match(self):
        """Test rule IDs that don't match pattern."""
        self.assertIsNone(infer_service_from_rule_id("invalid"))
        self.assertIsNone(infer_service_from_rule_id(""))
        self.assertIsNone(infer_service_from_rule_id(None))
    
    def test_unmapped_service(self):
        """Test service names not in mapping."""
        self.assertEqual(infer_service_from_rule_id("gws.custom.1.1"), "custom")


class TestParseRuleEntry(unittest.TestCase):
    """Test rule entry parsing."""
    
    def test_basic_parsing(self):
        """Test parsing basic rule entry."""
        entry = {
            "rule_id": "gws.gmail.1.1",
            "verdict": "PASS",
            "service": "gmail",
            "severity": "Critical"
        }
        
        rule = parse_rule_entry(entry)
        self.assertEqual(rule.rule_id, "gws.gmail.1.1")
        self.assertEqual(rule.verdict, Verdict.PASS)
        self.assertEqual(rule.service, "gmail")
        self.assertEqual(rule.severity, "Critical")
    
    def test_alternative_fields(self):
        """Test parsing with alternative field names."""
        entry = {
            "id": "test.rule",
            "result": "FAIL",
            "product": "drive",
            "priority": "High"
        }
        
        rule = parse_rule_entry(entry)
        self.assertEqual(rule.rule_id, "test.rule")
        self.assertEqual(rule.verdict, Verdict.FAIL)
        self.assertEqual(rule.service, "drive")
        self.assertEqual(rule.severity, "High")
    
    def test_service_inference(self):
        """Test service inference when not provided."""
        entry = {
            "rule_id": "gws.calendar.1.1",
            "verdict": "PASS"
        }
        
        rule = parse_rule_entry(entry)
        self.assertEqual(rule.service, "calendar")
    
    def test_with_weight_config(self):
        """Test parsing with weight configuration."""
        entry = {"rule_id": "gws.gmail.1.1", "verdict": "PASS"}
        weight_config = WeightConfig(weights={"gws.gmail.1.1": 5.0})
        
        rule = parse_rule_entry(entry, weight_config=weight_config)
        self.assertEqual(rule.weight, 5.0)


class TestIterRulesFromJSON(unittest.TestCase):
    """Test rule extraction from various JSON structures."""
    
    def test_direct_list(self):
        """Test extraction from direct list."""
        data = [
            {"rule_id": "rule1", "verdict": "PASS"},
            {"rule_id": "rule2", "verdict": "FAIL"}
        ]
        
        rules = list(iter_rules_from_json(data))
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["rule_id"], "rule1")
    
    def test_rules_key(self):
        """Test extraction from 'rules' key."""
        data = {
            "rules": [
                {"rule_id": "rule1", "verdict": "PASS"},
                {"rule_id": "rule2", "verdict": "FAIL"}
            ]
        }
        
        rules = list(iter_rules_from_json(data))
        self.assertEqual(len(rules), 2)
    
    def test_nested_structure(self):
        """Test extraction from nested structure."""
        data = {
            "Results": [
                {
                    "Rules": [
                        {"rule_id": "rule1", "verdict": "PASS"},
                        {"rule_id": "rule2", "verdict": "FAIL"}
                    ]
                }
            ]
        }
        
        rules = list(iter_rules_from_json(data))
        self.assertEqual(len(rules), 2)
    
    def test_service_structure(self):
        """Test extraction from service-based structure."""
        data = {
            "services": {
                "gmail": {
                    "rules": [
                        {"rule_id": "gmail.1", "verdict": "PASS"}
                    ]
                },
                "drive": {
                    "rules": [
                        {"rule_id": "drive.1", "verdict": "FAIL"}
                    ]
                }
            }
        }
        
        rules = list(iter_rules_from_json(data))
        self.assertEqual(len(rules), 2)
        # Service should be injected
        self.assertEqual(rules[0]["service"], "gmail")
        self.assertEqual(rules[1]["service"], "drive")


class TestLoadFunctions(unittest.TestCase):
    """Test file loading functions."""
    
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    def test_load_json_flexible(self, mock_file):
        """Test JSON loading."""
        data = load_json_flexible("test.json")
        self.assertEqual(data, {"test": "data"})
        mock_file.assert_called_once_with("test.json", "r", encoding="utf-8")
    
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json')
    def test_load_json_error(self, mock_file):
        """Test JSON loading error."""
        with self.assertRaises(ParsingError):
            load_json_flexible("test.json")
    
    @patch("builtins.open", new_callable=mock_open, read_data='test: value')
    def test_load_yaml_config(self, mock_file):
        """Test YAML loading."""
        data = load_yaml_config("test.yaml")
        self.assertEqual(data, {"test": "value"})
    
    def test_load_yaml_none(self):
        """Test YAML loading with None path."""
        data = load_yaml_config(None)
        self.assertEqual(data, {})
        
        data = load_yaml_config(None, default={"default": "value"})
        self.assertEqual(data, {"default": "value"})


if __name__ == "__main__":
    unittest.main()