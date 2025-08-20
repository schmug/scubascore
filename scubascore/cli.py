"""Command-line interface for SCuBA Scoring Kit."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .parsers import (
    load_json_flexible,
    parse_scuba_results,
    load_weight_config,
    load_service_weight_config,
    load_compensating_config,
)
from .scoring import compute_scores, get_score_summary
from .reporters import generate_reports
from .exceptions import ScubaScoreError

# Configure logging
def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog='scubascore',
        description='SCuBA Scoring Kit - Process CISA ScubaGoggles results to generate security scores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with all config files
  %(prog)s --input results.json --weights weights.yaml --service-weights service_weights.yaml --out-prefix output/report

  # Without compensating controls
  %(prog)s --input results.json --weights weights.yaml --out-prefix report

  # With custom output formats
  %(prog)s --input results.json --weights weights.yaml --out-prefix report --formats json csv

  # Verbose output for debugging
  %(prog)s --input results.json --weights weights.yaml --out-prefix report --verbose
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    # Required arguments
    required = parser.add_argument_group('required arguments')
    required.add_argument(
        '--input', '-i',
        required=True,
        type=Path,
        help='Path to ScubaGoggles JSON results file'
    )
    required.add_argument(
        '--out-prefix', '-o',
        required=True,
        type=Path,
        help='Output file prefix (directories will be created if needed)'
    )
    
    # Configuration files
    config = parser.add_argument_group('configuration files')
    config.add_argument(
        '--weights', '-w',
        type=Path,
        help='YAML file mapping rule IDs to numeric weights (default: all rules weight 1.0)'
    )
    config.add_argument(
        '--service-weights', '-s',
        type=Path,
        help='YAML file with service importance weights (default: built-in weights)'
    )
    config.add_argument(
        '--compensating', '-c',
        type=Path,
        help='YAML file defining compensating controls (optional)'
    )
    
    # Output options
    output = parser.add_argument_group('output options')
    output.add_argument(
        '--formats', '-f',
        nargs='+',
        choices=['json', 'csv', 'html', 'markdown'],
        default=['json', 'csv', 'html'],
        help='Output formats to generate (default: json csv html)'
    )
    output.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print console output'
    )
    
    # Logging options
    logging_group = parser.add_argument_group('logging options')
    logging_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    logging_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    
    # Advanced options
    advanced = parser.add_argument_group('advanced options')
    advanced.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate inputs without generating output files'
    )
    advanced.add_argument(
        '--strict',
        action='store_true',
        help='Exit with error if any rules cannot be parsed'
    )
    advanced.add_argument(
        '--config',
        type=Path,
        help='Load all settings from a configuration file'
    )
    
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Raises:
        ConfigurationError: If arguments are invalid
    """
    from .validators import validate_cli_args
    validate_cli_args(args)


def print_summary(result, outputs: dict, quiet: bool = False) -> None:
    """Print summary to console.
    
    Args:
        result: ScoreResult object
        outputs: Dictionary of output file paths
        quiet: Whether to suppress output
    """
    if quiet:
        return
    
    summary = get_score_summary(result)
    
    print("\n" + "="*60)
    print("SCuBA SCORING COMPLETE")
    print("="*60)
    
    print(f"\nOverall Score: {summary['overall_score']}%")
    print(f"Services Analyzed: {summary['services_analyzed']}")
    print(f"Services Meeting 80% Threshold: {summary['services_meeting_80_percent']}")
    
    print(f"\nTotal Rules Evaluated: {summary['total_rules_evaluated']}")
    print(f"  - Passed: {summary['total_passed']}")
    print(f"  - Failed: {summary['total_failed']}")
    
    print(f"\nData Quality:")
    print(f"  - Total Entries: {summary['data_quality']['total_entries']}")
    print(f"  - Skipped Entries: {summary['data_quality']['skipped_entries']}")
    print(f"  - Evaluation Rate: {summary['data_quality']['evaluation_rate']}%")
    
    print("\nOutput Files:")
    for fmt, path in outputs.items():
        print(f"  - {fmt.upper()}: {path}")
    
    print("="*60 + "\n")


def main(argv: Optional[list] = None) -> int:
    """Main entry point for CLI.
    
    Args:
        argv: Command-line arguments (default: sys.argv[1:])
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(args.verbose, args.quiet)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate arguments
        validate_args(args)
        
        # Load input data
        logger.info(f"Loading ScubaGoggles data from {args.input}")
        scuba_data = load_json_flexible(args.input)
        
        # Load configurations
        logger.info("Loading configurations")
        weight_config = load_weight_config(args.weights) if args.weights else None
        service_weight_config = load_service_weight_config(args.service_weights)
        compensating_config = load_compensating_config(args.compensating)
        
        # Parse rules
        logger.info("Parsing rules from ScubaGoggles data")
        rules = parse_scuba_results(scuba_data, weight_config, compensating_config)
        
        if not rules:
            logger.error("No rules found in input data")
            if args.strict:
                return 1
        
        logger.info(f"Parsed {len(rules)} rules")
        
        # Compute scores
        logger.info("Computing security scores")
        result = compute_scores(rules, service_weight_config)
        
        # Dry run check
        if args.dry_run:
            logger.info("Dry run complete - no files generated")
            print_summary(result, {}, args.quiet)
            return 0
        
        # Generate reports
        logger.info("Generating reports")
        outputs = generate_reports(result, args.out_prefix, args.formats)
        
        # Print summary
        print_summary(result, outputs, args.quiet)
        
        # Also output JSON summary for programmatic use
        if not args.quiet and args.pretty:
            print("\nJSON Summary:")
            print(json.dumps({
                "overall_score": result.overall_score,
                "output_files": {k: str(v) for k, v in outputs.items()},
            }, indent=2))
        
        return 0
        
    except ScubaScoreError as e:
        logger.error(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())