"""Integration tests for SCuBA Scoring Kit."""

import unittest
import tempfile
import json
import yaml
from pathlib import Path

from scubascore.parsers import (
    load_json_flexible, 
    parse_scuba_results,
    load_weight_config,
    load_service_weight_config,
    load_compensating_config
)
from scubascore.scoring import compute_scores
from scubascore.reporters import generate_reports


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.fixtures_dir = Path(__file__).parent / "fixtures"
    
    def test_basic_workflow(self):
        """Test basic end-to-end workflow."""
        # Load sample data
        json_data = load_json_flexible(self.fixtures_dir / "sample_scuba_output.json")
        
        # Parse rules
        rules = parse_scuba_results(json_data)
        self.assertEqual(len(rules), 6)
        
        # Compute scores
        result = compute_scores(rules)
        
        # Verify results
        self.assertIsNotNone(result.overall_score)
        self.assertIn("gmail", result.service_scores)
        self.assertIn("drive", result.service_scores)
        self.assertIn("common", result.service_scores)
        
        # Gmail should have 1 pass, 1 fail = 50%
        self.assertEqual(result.service_scores["gmail"].score, 50.0)
        
        # Drive should have 1 pass, 1 fail = 50%
        self.assertEqual(result.service_scores["drive"].score, 50.0)
        
        # Common should have 1 pass, 0 fail (1 N/A) = 100%
        self.assertEqual(result.service_scores["common"].score, 100.0)
    
    def test_with_weights(self):
        """Test workflow with custom weights."""
        # Create temporary weight config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "weights": {
                    "gws.gmail.1.1": 5.0,
                    "gws.gmail.2.1": 1.0,
                    "gws.drive.": 3.0,
                    "gws.common.": 2.0
                }
            }, f)
            weights_file = f.name
        
        try:
            # Load configurations
            json_data = load_json_flexible(self.fixtures_dir / "sample_scuba_output.json")
            weight_config = load_weight_config(weights_file)
            
            # Parse and score
            rules = parse_scuba_results(json_data, weight_config)
            result = compute_scores(rules)
            
            # Gmail: 5.0 passed, 1.0 failed = 5/6 = 83.33%
            self.assertAlmostEqual(result.service_scores["gmail"].score, 83.33, places=2)
            
            # Drive: 3.0 passed, 3.0 failed = 50%
            self.assertEqual(result.service_scores["drive"].score, 50.0)
            
        finally:
            Path(weights_file).unlink()
    
    def test_with_compensating_controls(self):
        """Test workflow with compensating controls."""
        # Create temporary compensating config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "compensating": {
                    "gws.gmail.2.1": "Alternative SPF implementation via gateway",
                    "gws.drive.2.1": "Manual DLP review process in place"
                }
            }, f)
            comp_file = f.name
        
        try:
            # Load configurations
            json_data = load_json_flexible(self.fixtures_dir / "sample_scuba_output.json")
            comp_config = load_compensating_config(comp_file)
            
            # Parse and score
            rules = parse_scuba_results(json_data, compensating_config=comp_config)
            result = compute_scores(rules)
            
            # Gmail: 1.0 passed, 1.0 failed with comp = 1.0 + 0.5 = 1.5/2.0 = 75%
            self.assertEqual(result.service_scores["gmail"].score, 75.0)
            
            # Drive: 1.0 passed, 1.0 failed with comp = 1.0 + 0.5 = 1.5/2.0 = 75%
            self.assertEqual(result.service_scores["drive"].score, 75.0)
            
        finally:
            Path(comp_file).unlink()
    
    def test_report_generation(self):
        """Test report generation."""
        # Load and process data
        json_data = load_json_flexible(self.fixtures_dir / "sample_scuba_output.json")
        rules = parse_scuba_results(json_data)
        result = compute_scores(rules)
        
        # Generate reports
        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = Path(tmpdir) / "test_report"
            outputs = generate_reports(result, output_prefix)
            
            # Verify all formats generated
            self.assertIn("json", outputs)
            self.assertIn("csv", outputs)
            self.assertIn("html", outputs)
            
            # Verify files exist
            for fmt, path in outputs.items():
                self.assertTrue(path.exists(), f"{fmt} file not created")
            
            # Verify JSON content
            with open(outputs["json"]) as f:
                json_data = json.load(f)
                self.assertEqual(json_data["overall_score"], result.overall_score)
                self.assertIn("per_service", json_data)
                self.assertIn("data_quality", json_data)
    
    def test_nested_json_structure(self):
        """Test parsing nested JSON structure."""
        json_data = load_json_flexible(self.fixtures_dir / "nested_scuba_output.json")
        rules = parse_scuba_results(json_data)
        
        self.assertEqual(len(rules), 2)
        # Check that alternative field names were parsed
        self.assertEqual(rules[0].rule_id, "gws.gmail.1.1")
        self.assertEqual(rules[0].verdict.value, "PASS")
        self.assertEqual(rules[1].rule_id, "gws.drive.1.1")
        self.assertEqual(rules[1].verdict.value, "FAIL")
    
    def test_service_based_structure(self):
        """Test parsing service-based JSON structure."""
        json_data = load_json_flexible(self.fixtures_dir / "service_based_output.json")
        rules = parse_scuba_results(json_data)
        
        self.assertEqual(len(rules), 3)
        # Check that services were injected
        gmail_rules = [r for r in rules if r.service == "gmail"]
        drive_rules = [r for r in rules if r.service == "drive"]
        
        self.assertEqual(len(gmail_rules), 2)
        self.assertEqual(len(drive_rules), 1)


if __name__ == "__main__":
    unittest.main()