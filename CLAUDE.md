# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The SCuBA Scoring Kit is a Python tool that processes CISA ScubaGoggles JSON output to generate weighted security scores for Google Workspace configurations. It provides comprehensive analysis with support for compensating controls and multiple output formats.

## Key Commands

### Running the Tool
```bash
# Basic usage
python scubascore.py --input <scubagoggles.json> --weights weights.yaml --service-weights service_weights.yaml --compensating compensating.yaml --out-prefix <output_prefix>

# Without compensating controls
python scubascore.py --input <scubagoggles.json> --weights weights.yaml --service-weights service_weights.yaml --out-prefix <output_prefix>

# Get help
python scubascore.py --help
```

### Testing
```bash
# Test if the script compiles correctly
python3 -m py_compile scubascore.py

# Run with sample files
python scubascore.py --input sample.json --weights weights.yaml --service-weights service_weights.yaml --compensating compensating.yaml --out-prefix output
```

## Architecture & Code Structure

### Single-File Architecture
The entire application is contained in `scubascore.py`, implementing:

1. **Schema-Tolerant JSON Parsing**: Multiple fallback strategies to handle various ScubaGoggles output formats
   - Primary path: `json_data.get("Rules", [])`
   - Secondary: Nested structures like `data["Results"][0]["Rules"]`
   - Comprehensive error handling for malformed data

2. **Service Inference Engine**: Uses regex patterns to map rules to Google Workspace services
   - Pattern: `gws.{service}.{rule}` (e.g., `gws.gmail.1.1`)
   - Automatic service detection from rule IDs
   - Fallback to "Unknown" service for unmatched rules

3. **Flexible Weight Mapping**: Supports both exact matches and prefix-based patterns
   - Weight hierarchy: Critical=5, High=3, Medium=2, Low=1
   - Service weights: Gmail/Drive/Common (1.0), Calendar/Groups (0.75), etc.
   - Prefix matching allows mapping entire rule families (e.g., `gws.common.`)

4. **Compensating Controls System**: 
   - Failed rules with documented controls receive 50% credit
   - Supports flexible rule ID formats
   - Tracks which controls were applied in reporting

### Key Functions

- `load_json_flexible()`: Robust JSON loader with multiple fallback strategies
- `infer_service_from_rule_id()`: Regex-based service detection
- `normalize_verdict()`: Handles PASS/FAIL/NA/UNKNOWN/ERROR variations
- `get_weight()`: Implements prefix-based weight matching
- `compute_scores()`: Core scoring algorithm with compensating controls
- `save_outputs()`: Generates JSON, CSV, and HTML reports

### Data Flow
1. Load ScubaGoggles JSON → Parse rules with schema tolerance
2. Load weight configurations → Map rules to severity weights
3. Apply compensating controls → Grant partial credit for mitigations
4. Calculate weighted scores → Per-service and overall scores
5. Generate reports → JSON (raw data), CSV (analysis), HTML (executive)

## Important Patterns & Conventions

### Weight Configuration Format
```yaml
# weights.yaml - Maps rule IDs to severity weights
gws.gmail.1.1: 5  # Critical
gws.common.: 3    # Prefix match for all common rules

# service_weights.yaml - Service importance multipliers
gmail: 1.0
drive: 1.0
common: 1.0
calendar: 0.75

# compensating.yaml - Documented mitigations
gws.gmail.1.1: "Alternative MFA implementation via third-party"
```

### Verdict Normalization
- Accepts: PASS, FAIL, N/A, UNKNOWN, ERROR (case-insensitive)
- Maps variations (e.g., "NA" → "N/A")
- Non-PASS verdicts contribute to failure counts

### Output Files
- `{prefix}_scores.json`: Complete scoring data with all details
- `{prefix}_analysis.csv`: Tabular format for spreadsheet analysis
- `{prefix}_report.html`: Executive-friendly visual report

## Development Guidelines

### When Modifying the Tool
1. Maintain schema tolerance - ScubaGoggles output format may vary
2. Preserve the weight hierarchy (Critical=5, High=3, Medium=2, Low=1)
3. Keep the 50% compensating control credit standard
4. Ensure all three output formats remain synchronized
5. Test with various ScubaGoggles JSON structures

### Adding New Features
- New weight categories: Update `DEFAULT_WEIGHTS` and weight mapping logic
- New services: Add to `DEFAULT_SERVICE_WEIGHTS` and update service inference
- New output formats: Follow the pattern in `save_outputs()`
- Schema changes: Add new parsing strategies to `load_json_flexible()`