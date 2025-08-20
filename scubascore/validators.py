"""Input validation for SCuBA Scoring Kit."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .exceptions import ConfigurationError, ParsingError
from .models import Verdict

logger = logging.getLogger(__name__)


def validate_json_structure(data: Any) -> None:
    """Validate that JSON data has expected structure.
    
    Args:
        data: Raw JSON data
        
    Raises:
        ParsingError: If structure is invalid
    """
    if data is None:
        raise ParsingError("JSON data is None")
    
    if not isinstance(data, (dict, list)):
        raise ParsingError(f"Expected dict or list, got {type(data).__name__}")
    
    # Try to find rules in the data
    found_rules = False
    
    if isinstance(data, list):
        found_rules = bool(data)
    elif isinstance(data, dict):
        # Check common keys
        for key in ["Rules", "rules", "results", "Results", "services"]:
            if key in data:
                found_rules = True
                break
    
    if not found_rules:
        logger.warning("No obvious rule containers found in JSON structure")


def validate_rule_entry(entry: Dict[str, Any]) -> List[str]:
    """Validate a single rule entry.
    
    Args:
        entry: Rule entry dictionary
        
    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []
    
    # Check for rule ID
    id_fields = ["rule_id", "id", "rule", "name", "check_id", "control_id"]
    if not any(entry.get(field) for field in id_fields):
        warnings.append("No rule identifier found")
    
    # Check for verdict
    verdict_fields = ["verdict", "result", "status", "outcome", "compliance_status"]
    if not any(entry.get(field) for field in verdict_fields):
        warnings.append("No verdict/result field found")
    
    # Check verdict value if present
    for field in verdict_fields:
        if field in entry:
            try:
                # This will log warning if invalid
                from .parsers import normalize_verdict
                verdict = normalize_verdict(entry[field])
                if verdict == Verdict.UNKNOWN and entry[field] not in ["UNKNOWN", "ERROR", None]:
                    warnings.append(f"Unrecognized verdict value: {entry[field]}")
            except Exception:
                warnings.append(f"Invalid verdict value: {entry[field]}")
            break
    
    return warnings


def validate_weight_config(config: Dict[str, Any]) -> None:
    """Validate weight configuration.
    
    Args:
        config: Weight configuration dictionary
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ConfigurationError(f"Weight config must be a dict, got {type(config).__name__}")
    
    # Extract weights
    weights = config.get("weights", config)
    
    if not isinstance(weights, dict):
        raise ConfigurationError("Weights must be a dictionary")
    
    # Validate each weight
    for key, value in weights.items():
        if not isinstance(key, str):
            raise ConfigurationError(f"Weight key must be string, got {type(key).__name__}")
        
        if not isinstance(value, (int, float)):
            raise ConfigurationError(f"Weight for '{key}' must be numeric, got {type(value).__name__}")
        
        if value < 0:
            raise ConfigurationError(f"Weight for '{key}' must be non-negative, got {value}")
        
        if value > 10:
            logger.warning(f"Unusually high weight for '{key}': {value}")


def validate_service_weight_config(config: Dict[str, Any]) -> None:
    """Validate service weight configuration.
    
    Args:
        config: Service weight configuration dictionary
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ConfigurationError(f"Service weight config must be a dict, got {type(config).__name__}")
    
    # Extract service weights
    service_weights = config.get("service_weights", config)
    
    if not isinstance(service_weights, dict):
        raise ConfigurationError("Service weights must be a dictionary")
    
    total_weight = 0.0
    
    # Validate each service weight
    for service, weight in service_weights.items():
        if not isinstance(service, str):
            raise ConfigurationError(f"Service name must be string, got {type(service).__name__}")
        
        if not isinstance(weight, (int, float)):
            raise ConfigurationError(f"Weight for service '{service}' must be numeric, got {type(weight).__name__}")
        
        if weight < 0:
            raise ConfigurationError(f"Weight for service '{service}' must be non-negative, got {weight}")
        
        if weight > 1.0:
            logger.warning(f"Service weight for '{service}' is greater than 1.0: {weight}")
        
        total_weight += weight
    
    # Warn if weights don't sum to 1.0 (approximately)
    if abs(total_weight - 1.0) > 0.01 and total_weight > 0:
        logger.warning(f"Service weights sum to {total_weight:.2f}, not 1.0")


def validate_compensating_config(config: Dict[str, Any]) -> None:
    """Validate compensating control configuration.
    
    Args:
        config: Compensating control configuration dictionary
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ConfigurationError(f"Compensating config must be a dict, got {type(config).__name__}")
    
    # Extract controls
    controls = config.get("compensating", config)
    
    if not isinstance(controls, dict):
        raise ConfigurationError("Compensating controls must be a dictionary")
    
    # Validate each control
    for rule_id, control in controls.items():
        if not isinstance(rule_id, str):
            raise ConfigurationError(f"Rule ID must be string, got {type(rule_id).__name__}")
        
        if isinstance(control, dict):
            # Complex control with metadata
            if "rationale" not in control and "description" not in control:
                logger.warning(f"Compensating control for '{rule_id}' has no rationale/description")
        elif not isinstance(control, str):
            raise ConfigurationError(
                f"Compensating control for '{rule_id}' must be string or dict, "
                f"got {type(control).__name__}"
            )


def validate_output_path(path: Union[str, Path]) -> Path:
    """Validate output path and create parent directories.
    
    Args:
        path: Output file path or prefix
        
    Returns:
        Validated Path object
        
    Raises:
        ConfigurationError: If path is invalid
    """
    try:
        path = Path(path)
    except Exception as e:
        raise ConfigurationError(f"Invalid output path: {e}") from e
    
    # Check if parent directory exists or can be created
    parent = path.parent
    if parent and not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {parent}")
        except Exception as e:
            raise ConfigurationError(f"Cannot create output directory {parent}: {e}") from e
    
    # Check if we can write to the location
    if path.exists() and path.is_dir():
        raise ConfigurationError(f"Output path is a directory: {path}")
    
    return path


def validate_cli_args(args) -> None:
    """Validate all CLI arguments comprehensively.
    
    Args:
        args: Parsed argparse namespace
        
    Raises:
        ConfigurationError: If any argument is invalid
    """
    # Validate input file
    if not args.input.exists():
        raise ConfigurationError(f"Input file not found: {args.input}")
    
    if not args.input.is_file():
        raise ConfigurationError(f"Input path is not a file: {args.input}")
    
    # Validate output prefix
    validate_output_path(args.out_prefix)
    
    # Validate optional config files
    if args.weights and not args.weights.exists():
        raise ConfigurationError(f"Weights file not found: {args.weights}")
    
    if args.service_weights and not args.service_weights.exists():
        raise ConfigurationError(f"Service weights file not found: {args.service_weights}")
    
    if args.compensating and not args.compensating.exists():
        raise ConfigurationError(f"Compensating controls file not found: {args.compensating}")
    
    # Validate output formats
    valid_formats = {"json", "csv", "html", "markdown"}
    for fmt in args.formats:
        if fmt not in valid_formats:
            raise ConfigurationError(f"Invalid output format: {fmt}")
    
    # Validate conflicting options
    if args.verbose and args.quiet:
        raise ConfigurationError("Cannot use --verbose and --quiet together")