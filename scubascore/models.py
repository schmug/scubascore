"""Data models for SCuBA Scoring Kit."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum


class Verdict(Enum):
    """Enumeration of possible rule verdicts."""
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "NA"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass
class Rule:
    """Represents a single security rule from ScubaGoggles output."""
    rule_id: str
    verdict: Verdict
    service: Optional[str] = None
    severity: Optional[str] = None
    weight: float = 1.0
    compensating_control: Optional[str] = None
    raw_data: Dict = field(default_factory=dict)

    def is_evaluated(self) -> bool:
        """Check if the rule contributes to scoring."""
        return self.verdict in (Verdict.PASS, Verdict.FAIL)

    def get_score_contribution(self) -> float:
        """Calculate the rule's contribution to the overall score."""
        if self.verdict == Verdict.PASS:
            return self.weight
        elif self.verdict == Verdict.FAIL:
            # Compensating controls grant 50% credit
            return self.weight * 0.5 if self.compensating_control else 0.0
        return 0.0


@dataclass
class ServiceScore:
    """Scoring details for a specific service."""
    service_name: str
    score: Optional[float] = None
    evaluated_weight: float = 0.0
    passed_weight: float = 0.0
    passed_rules: List[Tuple[str, float]] = field(default_factory=list)
    failed_rules: List[Tuple[str, float, bool]] = field(default_factory=list)  # (id, weight, has_compensating)
    
    @property
    def passed_count(self) -> int:
        """Count of passed rules."""
        return len(self.passed_rules)
    
    @property
    def failed_count(self) -> int:
        """Count of failed rules."""
        return len(self.failed_rules)

    def calculate_score(self) -> None:
        """Calculate the service score as a percentage."""
        if self.evaluated_weight > 0:
            self.score = round((self.passed_weight / self.evaluated_weight) * 100.0, 2)


@dataclass
class DataQuality:
    """Data quality metrics for the scoring run."""
    total_entries: int = 0
    unknown_entries: int = 0
    na_entries: int = 0
    error_entries: int = 0
    
    @property
    def unknown_or_error_entries(self) -> int:
        """Combined count of unknown and error entries."""
        return self.unknown_entries + self.error_entries


@dataclass
class ScoreResult:
    """Complete scoring results."""
    generated_at: datetime
    overall_score: Optional[float]
    service_scores: Dict[str, ServiceScore]
    data_quality: DataQuality
    configuration: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat() + "Z",
            "overall_score": self.overall_score,
            "per_service": {
                name: {
                    "score": svc.score,
                    "evaluated_weight": svc.evaluated_weight,
                    "passed_weight": svc.passed_weight,
                    "passed_count": svc.passed_count,
                    "failed_count": svc.failed_count,
                }
                for name, svc in self.service_scores.items()
            },
            "data_quality": {
                "unknown_or_error_entries": self.data_quality.unknown_or_error_entries,
                "total_entries_seen": self.data_quality.total_entries,
            },
            "configuration": self.configuration,
        }


@dataclass 
class WeightConfig:
    """Weight configuration mapping."""
    weights: Dict[str, float] = field(default_factory=dict)
    
    def get_weight(self, rule_id: str, default: float = 1.0) -> float:
        """Get weight for a rule ID, supporting prefix matching."""
        # Exact match
        if rule_id in self.weights:
            return self.weights[rule_id]
        
        # Prefix match (longest prefix wins)
        best_prefix = ""
        for key in self.weights:
            if rule_id.startswith(key) and len(key) > len(best_prefix):
                best_prefix = key
        
        return self.weights.get(best_prefix, default)


@dataclass
class ServiceWeightConfig:
    """Service weight configuration."""
    service_weights: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default weights if empty."""
        if not self.service_weights:
            self.service_weights = {
                "gmail": 0.20,
                "drive": 0.20,
                "common": 0.20,
                "groups": 0.10,
                "chat": 0.10,
                "meet": 0.05,
                "calendar": 0.05,
                "classroom": 0.05,
                "sites": 0.05,
            }


@dataclass
class CompensatingControlConfig:
    """Compensating control configuration."""
    controls: Dict[str, Union[str, Dict[str, any]]] = field(default_factory=dict)
    
    def get_control(self, rule_id: str) -> Optional[str]:
        """Get compensating control description for a rule."""
        control = self.controls.get(rule_id)
        if isinstance(control, dict):
            return control.get("rationale", str(control))
        return str(control) if control else None