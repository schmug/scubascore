"""SCuBA Scoring Kit - Security Configuration Benchmarking and Analysis.

A tool for processing CISA ScubaGoggles JSON results to generate weighted 
security scores for Google Workspace configurations.
"""

__version__ = "1.0.0"
__author__ = "SCuBA Team"

from .models import Rule, ScoreResult, ServiceScore
from .parsers import load_json_flexible, parse_scuba_results
from .scoring import compute_scores
from .reporters import generate_reports

__all__ = [
    "Rule",
    "ScoreResult", 
    "ServiceScore",
    "load_json_flexible",
    "parse_scuba_results",
    "compute_scores",
    "generate_reports",
]