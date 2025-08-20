"""Score computation logic for SCuBA Scoring Kit."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .models import (
    Rule,
    ScoreResult,
    ServiceScore,
    DataQuality,
    Verdict,
    ServiceWeightConfig,
)
from .exceptions import ScoringError

logger = logging.getLogger(__name__)


def compute_scores(
    rules: List[Rule],
    service_weights: Optional[ServiceWeightConfig] = None,
) -> ScoreResult:
    """Compute security scores from parsed rules.
    
    Args:
        rules: List of parsed Rule objects
        service_weights: Service weight configuration
        
    Returns:
        Complete ScoreResult object
        
    Raises:
        ScoringError: If scoring calculation fails
    """
    if not rules:
        logger.warning("No rules provided for scoring")
        return ScoreResult(
            generated_at=datetime.utcnow(),
            overall_score=None,
            service_scores={},
            data_quality=DataQuality(),
        )
    
    # Initialize service weights
    if not service_weights:
        service_weights = ServiceWeightConfig()
    
    # Group rules by service and calculate scores
    service_aggregates = defaultdict(lambda: {
        "evaluated_weight": 0.0,
        "passed_weight": 0.0,
        "passed_rules": [],
        "failed_rules": [],
    })
    
    data_quality = DataQuality(total_entries=len(rules))
    
    for rule in rules:
        service = rule.service or "unspecified"
        
        if rule.verdict == Verdict.PASS:
            service_aggregates[service]["evaluated_weight"] += rule.weight
            service_aggregates[service]["passed_weight"] += rule.weight
            service_aggregates[service]["passed_rules"].append((rule.rule_id, rule.weight))
            
        elif rule.verdict == Verdict.FAIL:
            # Apply compensating control credit
            credit = rule.weight * 0.5 if rule.compensating_control else 0.0
            service_aggregates[service]["evaluated_weight"] += rule.weight
            service_aggregates[service]["passed_weight"] += credit
            service_aggregates[service]["failed_rules"].append(
                (rule.rule_id, rule.weight, bool(rule.compensating_control))
            )
            
        elif rule.verdict == Verdict.NA:
            data_quality.na_entries += 1
            
        elif rule.verdict == Verdict.ERROR:
            data_quality.error_entries += 1
            
        else:  # UNKNOWN
            data_quality.unknown_entries += 1
    
    # Create ServiceScore objects
    service_scores = {}
    for service_name, aggregate in service_aggregates.items():
        service_score = ServiceScore(
            service_name=service_name,
            evaluated_weight=round(aggregate["evaluated_weight"], 2),
            passed_weight=round(aggregate["passed_weight"], 2),
            passed_rules=aggregate["passed_rules"],
            failed_rules=aggregate["failed_rules"],
        )
        service_score.calculate_score()
        service_scores[service_name] = service_score
    
    # Calculate overall score
    overall_score = calculate_overall_score(service_scores, service_weights)
    
    logger.info(f"Computed scores for {len(service_scores)} services")
    
    return ScoreResult(
        generated_at=datetime.utcnow(),
        overall_score=overall_score,
        service_scores=service_scores,
        data_quality=data_quality,
    )


def calculate_overall_score(
    service_scores: Dict[str, ServiceScore],
    service_weights: ServiceWeightConfig,
) -> Optional[float]:
    """Calculate weighted overall score from service scores.
    
    Args:
        service_scores: Dictionary of service scores
        service_weights: Service weight configuration
        
    Returns:
        Overall score as percentage or None if no data
    """
    total_weight = 0.0
    weighted_sum = 0.0
    
    for service_name, service_score in service_scores.items():
        if service_score.score is not None:
            # Get service weight, default to 0.1 if not configured
            service_weight = service_weights.service_weights.get(service_name, 0.1)
            total_weight += service_weight
            weighted_sum += service_weight * service_score.score
    
    if total_weight > 0:
        overall = weighted_sum / total_weight
        return round(overall, 2)
    
    return None


def get_failed_rules_by_severity(
    rules: List[Rule],
    weight_thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, List[Rule]]:
    """Group failed rules by severity level.
    
    Args:
        rules: List of Rule objects
        weight_thresholds: Mapping of severity names to weight thresholds
        
    Returns:
        Dictionary mapping severity levels to lists of failed rules
    """
    if not weight_thresholds:
        weight_thresholds = {
            "Critical": 5.0,
            "High": 3.0,
            "Medium": 2.0,
            "Low": 1.0,
        }
    
    failed_by_severity = defaultdict(list)
    
    for rule in rules:
        if rule.verdict == Verdict.FAIL and not rule.compensating_control:
            # Determine severity from weight
            severity = "Low"
            for sev_name, threshold in sorted(
                weight_thresholds.items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                if rule.weight >= threshold:
                    severity = sev_name
                    break
            
            failed_by_severity[severity].append(rule)
    
    return dict(failed_by_severity)


def get_score_summary(result: ScoreResult) -> Dict[str, any]:
    """Generate a summary of scoring results.
    
    Args:
        result: ScoreResult object
        
    Returns:
        Dictionary with summary statistics
    """
    total_passed = sum(s.passed_count for s in result.service_scores.values())
    total_failed = sum(s.failed_count for s in result.service_scores.values())
    total_evaluated = total_passed + total_failed
    
    services_meeting_threshold = sum(
        1 for s in result.service_scores.values() 
        if s.score is not None and s.score >= 80.0
    )
    
    return {
        "overall_score": result.overall_score,
        "services_analyzed": len(result.service_scores),
        "services_meeting_80_percent": services_meeting_threshold,
        "total_rules_evaluated": total_evaluated,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "data_quality": {
            "total_entries": result.data_quality.total_entries,
            "skipped_entries": result.data_quality.unknown_or_error_entries,
            "evaluation_rate": round(
                (total_evaluated / result.data_quality.total_entries * 100)
                if result.data_quality.total_entries > 0 else 0,
                2
            ),
        },
    }