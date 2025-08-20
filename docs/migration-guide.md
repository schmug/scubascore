# Migration Guide: v0.x to v1.0

This guide helps you migrate from the legacy monolithic script to the new modular version of SCuBA Scoring Kit.

## Overview of Changes

The SCuBA Scoring Kit has been completely refactored from a single Python script to a properly packaged Python application. While the core functionality remains the same, the way you interact with the tool has improved.

## Installation

### Old Method
```bash
# Copy the script
cp scubascore.py /usr/local/bin/
chmod +x /usr/local/bin/scubascore.py
```

### New Method
```bash
# Clone and install
git clone https://github.com/yourusername/scubascore.git
cd scubascore
pip install -e .

# Or install from PyPI (when published)
pip install scubascore
```

## Command Line Usage

### Basic Command - No Changes!
The basic command structure remains the same:

```bash
# Old
python scubascore.py --input data.json --weights weights.yaml --out-prefix output

# New
scubascore --input data.json --weights weights.yaml --out-prefix output
```

### New Options
The new version adds several helpful options:

```bash
# Validate without generating files
scubascore --input data.json --weights weights.yaml --out-prefix output --dry-run

# Control output verbosity
scubascore --input data.json --weights weights.yaml --out-prefix output --verbose
scubascore --input data.json --weights weights.yaml --out-prefix output --quiet

# Generate specific formats
scubascore --input data.json --weights weights.yaml --out-prefix output --formats json csv

# Pretty-print summary
scubascore --input data.json --weights weights.yaml --out-prefix output --pretty
```

## Configuration Files

Configuration files remain compatible, but the examples have moved:

### Old Location
```
./weights.yaml
./service_weights.yaml
./compensating.yaml
```

### New Location
```
./examples/sample_configs/weights.yaml
./examples/sample_configs/service_weights.yaml
./examples/sample_configs/compensating.yaml
```

Your existing configuration files will work without modification.

## Output Files

Output files remain exactly the same:
- `{prefix}_scores.json` - Detailed scoring data
- `{prefix}_analysis.csv` - Tabular analysis (previously `_scores.csv`)
- `{prefix}_report.html` - Executive report (previously `_summary.html`)

## Python API Usage

### Old Method
```python
# Not recommended - importing from script
import scubascore
# Limited API access
```

### New Method
```python
from scubascore import (
    load_json_flexible,
    parse_scuba_results,
    compute_scores,
    generate_reports
)

# Load and process data
json_data = load_json_flexible("scuba_results.json")
rules = parse_scuba_results(json_data)
result = compute_scores(rules)
outputs = generate_reports(result, "output_prefix")
```

## Error Handling

### Old Behavior
- Generic error messages
- Script exits on any error
- Limited validation

### New Behavior
- Detailed error messages with context
- Specific exception types
- Comprehensive validation with warnings
- Option to continue on non-fatal errors

Example:
```bash
# Old error
Error: Invalid JSON

# New error
ParsingError: Invalid JSON in /path/to/file.json: Expecting property name enclosed in double quotes: line 10 column 5 (char 234)
```

## Breaking Changes

1. **Installation Required**: The tool must now be installed via pip
2. **Import Path**: If importing as a module, use `from scubascore import ...`
3. **File Names**: Some output file names have changed:
   - `_scores.csv` → `_analysis.csv`
   - `_summary.html` → `_report.html`

## New Features to Explore

1. **Type Safety**: Full type hints for better IDE support
2. **Validation**: Input validation with helpful warnings
3. **Logging**: Structured logging with configurable levels
4. **Testing**: Run tests with `pytest` to verify functionality
5. **Documentation**: Comprehensive API documentation

## Common Migration Scenarios

### Scenario 1: Cron Job
```bash
# Old crontab entry
0 2 * * * /usr/bin/python /opt/scripts/scubascore.py --input /data/results.json --weights /etc/scuba/weights.yaml --out-prefix /reports/daily

# New crontab entry (after pip install)
0 2 * * * /usr/local/bin/scubascore --input /data/results.json --weights /etc/scuba/weights.yaml --out-prefix /reports/daily
```

### Scenario 2: Shell Script Integration
```bash
#!/bin/bash
# Old
python /path/to/scubascore.py --input $INPUT --weights $WEIGHTS --out-prefix $OUTPUT

# New
scubascore --input $INPUT --weights $WEIGHTS --out-prefix $OUTPUT
```

### Scenario 3: Python Script Integration
```python
# Old
import subprocess
subprocess.run(["python", "scubascore.py", "--input", "data.json"])

# New - Option 1: Use CLI
import subprocess
subprocess.run(["scubascore", "--input", "data.json"])

# New - Option 2: Use API
from scubascore import load_json_flexible, parse_scuba_results, compute_scores

data = load_json_flexible("data.json")
rules = parse_scuba_results(data)
result = compute_scores(rules)
print(f"Overall score: {result.overall_score}%")
```

## Getting Help

- Run `scubascore --help` for command-line options
- Check the README.md for detailed documentation
- Report issues on GitHub
- Review the examples in `examples/` directory

## Rollback Plan

If you need to temporarily rollback:

1. The old script is preserved at `legacy/scubascore_v0.py`
2. Copy it back to your preferred location
3. Use as before with `python scubascore_v0.py ...`

Note: The legacy version is no longer maintained and will not receive updates.