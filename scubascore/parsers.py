"""Parsers for various input formats."""

import json
import re
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

import yaml

from .models import Rule, Verdict, WeightConfig, ServiceWeightConfig, CompensatingControlConfig
from .exceptions import ParsingError, ConfigurationError

logger = logging.getLogger(__name__)

# Compiled regex for better performance
SERVICE_PATTERN = re.compile(r"^[a-zA-Z0-9]+\.([a-z_]+)\.?")

# Service name mapping
SERVICE_MAPPING = {
    "gmail": "gmail",
    "drive": "drive", 
    "chat": "chat",
    "meet": "meet",
    "calendar": "calendar",
    "groups": "groups",
    "classroom": "classroom",
    "sites": "sites",
    "common": "common",
}


def load_json_flexible(path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON file with flexible error handling.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        ParsingError: If JSON cannot be parsed
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {path}: {e}")
        raise ParsingError(f"Invalid JSON in {path}: {e}") from e
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        raise ParsingError(f"Cannot read {path}: {e}") from e


def load_yaml_config(path: Optional[Union[str, Path]], default: Any = None) -> Dict[str, Any]:
    """Load YAML configuration file.
    
    Args:
        path: Path to YAML file (optional)
        default: Default value if path is None
        
    Returns:
        Parsed YAML data or default
        
    Raises:
        ConfigurationError: If YAML cannot be parsed
    """
    if not path:
        return default or {}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML from {path}: {e}")
        raise ConfigurationError(f"Invalid YAML in {path}: {e}") from e
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        raise ConfigurationError(f"Cannot read {path}: {e}") from e


def normalize_verdict(value: Any) -> Verdict:
    """Normalize various verdict representations to standard enum.
    
    Args:
        value: Raw verdict value
        
    Returns:
        Normalized Verdict enum
    """
    if value is None:
        return Verdict.UNKNOWN
    
    v = str(value).strip().upper()
    
    # Map common variants
    if v in {"PASS", "PASSED", "TRUE", "SUCCESS", "OK"}:
        return Verdict.PASS
    elif v in {"FAIL", "FAILED", "FALSE", "FAILURE"}:
        return Verdict.FAIL
    elif v in {"N/A", "NA", "NOT APPLICABLE", "NOT_APPLICABLE", "NOTAPPLICABLE"}:
        return Verdict.NA
    elif v in {"UNKNOWN", "ERROR", "UNDEFINED"}:
        return Verdict.UNKNOWN
    elif v in {"WARNING", "WARN"}:
        # Warnings are typically non-blocking issues, treat as NA
        return Verdict.NA
    elif "NO EVENTS FOUND" in v or v == "NO EVENTS FOUND":
        # No data to evaluate, treat as NA
        return Verdict.NA
    elif v in {"MANUAL", "REQUIRES MANUAL CHECK"}:
        # Manual checks cannot be automated, treat as NA
        return Verdict.NA
    
    logger.warning(f"Unknown verdict value: {value}")
    return Verdict.UNKNOWN


def infer_service_from_rule_id(rule_id: Optional[str]) -> Optional[str]:
    """Infer service name from rule ID pattern.
    
    Args:
        rule_id: Rule identifier
        
    Returns:
        Inferred service name or None
    """
    if not rule_id:
        return None
    
    match = SERVICE_PATTERN.match(rule_id)
    if match:
        candidate = match.group(1)
        return SERVICE_MAPPING.get(candidate, candidate)
    
    return None


def parse_rule_entry(
    entry: Dict[str, Any],
    default_service: Optional[str] = None,
    weight_config: Optional[WeightConfig] = None,
    compensating_config: Optional[CompensatingControlConfig] = None,
) -> Rule:
    """Parse a single rule entry from various formats.
    
    Args:
        entry: Raw rule data
        default_service: Default service if not found in entry
        weight_config: Weight configuration for rule weights
        compensating_config: Compensating control configuration
        
    Returns:
        Parsed Rule object
    """
    # Extract rule ID with multiple fallbacks
    rule_id = (
        entry.get("rule_id") or 
        entry.get("id") or 
        entry.get("rule") or 
        entry.get("name") or 
        entry.get("check_id") or
        entry.get("control_id") or
        entry.get("Control ID") or  # ScubaGoggles v0.5.0
        "unknown"
    )
    
    # Extract and normalize verdict
    verdict = normalize_verdict(
        entry.get("verdict") or 
        entry.get("result") or 
        entry.get("Result") or  # ScubaGoggles v0.5.0
        entry.get("status") or
        entry.get("outcome") or
        entry.get("compliance_status")
    )
    
    # Extract service
    service = (
        entry.get("service") or 
        entry.get("product") or 
        entry.get("category") or
        entry.get("component") or
        default_service
    )
    
    if not service:
        service = infer_service_from_rule_id(rule_id)
    
    # Extract severity
    severity = (
        entry.get("severity") or 
        entry.get("priority") or 
        entry.get("weight_class") or
        entry.get("criticality") or
        entry.get("Criticality")  # ScubaGoggles v0.5.0
    )
    
    # Get weight from config
    weight = 1.0
    if weight_config:
        weight = weight_config.get_weight(rule_id)
    
    # Get compensating control
    compensating_control = None
    if compensating_config:
        compensating_control = compensating_config.get_control(rule_id)
    
    # Extract requirement text
    requirement = (
        entry.get("requirement") or
        entry.get("Requirement") or
        entry.get("description") or
        entry.get("Description")
    )
    
    # Extract or construct documentation URL
    documentation_url = entry.get("documentation_url") or entry.get("DocumentationURL")
    if not documentation_url:
        # Try to construct from group URL if available
        group_url = entry.get("GroupReferenceURL")
        if group_url and rule_id:
            # Extract control number from rule_id (e.g., "GWS.CALENDAR.1.1v0.5" -> "1.1")
            import re
            match = re.search(r'\.(\d+\.\d+)', rule_id)
            if match:
                control_num = match.group(1)
                # Construct specific control URL by appending control number
                documentation_url = f"{group_url}#{control_num.replace('.', '')}"
    
    return Rule(
        rule_id=rule_id,
        verdict=verdict,
        service=service,
        severity=severity,
        weight=weight,
        compensating_control=compensating_control,
        documentation_url=documentation_url,
        requirement=requirement,
        raw_data=entry,
    )


def iter_rules_from_json(data: Any) -> Iterator[Dict[str, Any]]:
    """Extract rule entries from various JSON structures.
    
    Args:
        data: Raw JSON data
        
    Yields:
        Rule entry dictionaries
    """
    # Handle direct list
    if isinstance(data, list):
        yield from data
        return
    
    if not isinstance(data, dict):
        logger.warning(f"Unexpected data type: {type(data)}")
        return
    
    # Try common top-level keys
    for key in ["Rules", "rules", "results", "checks", "findings", "items", "controls"]:
        if key in data and isinstance(data[key], list):
            logger.debug(f"Found rules under key '{key}'")
            yield from data[key]
            return
    
    # Try nested structures like {"Results": [{"Rules": [...]}]}
    for key in ["Results", "results"]:
        if key in data and isinstance(data[key], list):
            for item in data[key]:
                if isinstance(item, dict):
                    for rules_key in ["Rules", "rules"]:
                        if rules_key in item and isinstance(item[rules_key], list):
                            logger.debug(f"Found rules under {key}[*].{rules_key}")
                            yield from item[rules_key]
                            return
    
    # Handle ScubaGoggles v0.5.0 structure: {"Results": {"service": [{"Controls": [...]}]}}
    results_data = data.get("Results") or data.get("results")
    if isinstance(results_data, dict):
        logger.debug("Found ScubaGoggles v0.5.0 Results structure")
        for service_name, groups in results_data.items():
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict) and "Controls" in group:
                        group_url = group.get("GroupReferenceURL", "")
                        for control in group["Controls"]:
                            if isinstance(control, dict):
                                # Inject service name if not present
                                if "service" not in control:
                                    control = {**control, "service": service_name}
                                # Inject group URL for control-specific URL construction
                                if "GroupReferenceURL" not in control and group_url:
                                    control["GroupReferenceURL"] = group_url
                                yield control
        return
    
    # Handle service-based structure: {"services": {"gmail": {"rules": [...]}}}
    services_data = data.get("services") or data.get("Services")
    if isinstance(services_data, dict):
        logger.debug("Found service-based structure")
        for service_name, service_data in services_data.items():
            if isinstance(service_data, dict):
                for key in ["rules", "results", "checks"]:
                    if key in service_data and isinstance(service_data[key], list):
                        for entry in service_data[key]:
                            if isinstance(entry, dict):
                                # Inject service name if not present
                                if "service" not in entry:
                                    entry = {**entry, "service": service_name}
                                yield entry
        return
    
    # Last resort: find any list in values
    logger.warning("Using fallback rule extraction")
    for value in data.values():
        if isinstance(value, list) and value:
            # Check if it looks like rules
            if isinstance(value[0], dict) and any(
                k in value[0] for k in ["rule_id", "id", "verdict", "result", "status"]
            ):
                yield from value
                return


def parse_scuba_results(
    json_data: Dict[str, Any],
    weight_config: Optional[WeightConfig] = None,
    compensating_config: Optional[CompensatingControlConfig] = None,
) -> List[Rule]:
    """Parse ScubaGoggles results into Rule objects.
    
    Args:
        json_data: Raw ScubaGoggles JSON data
        weight_config: Weight configuration
        compensating_config: Compensating control configuration
        
    Returns:
        List of parsed Rule objects
    """
    # Validate JSON structure
    from .validators import validate_json_structure
    validate_json_structure(json_data)
    
    rules = []
    
    for entry in iter_rules_from_json(json_data):
        try:
            rule = parse_rule_entry(entry, None, weight_config, compensating_config)
            rules.append(rule)
        except Exception as e:
            logger.warning(f"Failed to parse rule entry: {e}")
            logger.debug(f"Problematic entry: {entry}")
    
    logger.info(f"Parsed {len(rules)} rules from JSON")
    return rules


def load_weight_config(path: Optional[Union[str, Path]]) -> WeightConfig:
    """Load weight configuration from YAML file.
    
    Args:
        path: Path to weights YAML file
        
    Returns:
        WeightConfig object
    """
    data = load_yaml_config(path, {})
    
    # Validate configuration
    from .validators import validate_weight_config
    validate_weight_config(data)
    
    weights = data.get("weights", data)
    return WeightConfig(weights=weights)


def load_service_weight_config(path: Optional[Union[str, Path]]) -> ServiceWeightConfig:
    """Load service weight configuration from YAML file.
    
    Args:
        path: Path to service weights YAML file
        
    Returns:
        ServiceWeightConfig object
    """
    data = load_yaml_config(path, {})
    
    # Validate configuration
    from .validators import validate_service_weight_config
    validate_service_weight_config(data)
    
    service_weights = data.get("service_weights", data)
    return ServiceWeightConfig(service_weights=service_weights)


def load_compensating_config(path: Optional[Union[str, Path]]) -> CompensatingControlConfig:
    """Load compensating control configuration from YAML file.
    
    Args:
        path: Path to compensating controls YAML file
        
    Returns:
        CompensatingControlConfig object
    """
    data = load_yaml_config(path, {})
    
    # Validate configuration
    from .validators import validate_compensating_config
    validate_compensating_config(data)
    
    controls = data.get("compensating", data)
    return CompensatingControlConfig(controls=controls)