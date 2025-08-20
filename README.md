# SCuBA Scoring Kit

[![CI](https://github.com/yourusername/scubascore/workflows/CI/badge.svg)](https://github.com/yourusername/scubascore/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive security scoring tool for CISA ScubaGoggles output, providing weighted security assessments for Google Workspace configurations.

## Features

- **Schema-Tolerant Parsing**: Handles various ScubaGoggles JSON output formats
- **Flexible Weight System**: Configure rule weights based on criticality
- **Compensating Controls**: Grant partial credit for documented mitigations
- **Multiple Output Formats**: JSON, CSV, HTML, and Markdown reports
- **Service-Based Scoring**: Weighted scores for each Google Workspace service
- **Comprehensive Validation**: Input validation with helpful error messages
- **Type-Safe**: Full type hints for better IDE support and reliability

## Installation

### From Source

```bash
git clone https://github.com/yourusername/scubascore.git
cd scubascore
pip install -e .
```

### Using pip

```bash
pip install scubascore
```

## Quick Start

1. **Run ScubaGoggles** to generate a JSON results file
2. **Configure weights** (optional - uses sensible defaults)
3. **Run SCuBA Scoring**:

```bash
scubascore --input ScubaResults.json \
           --weights weights.yaml \
           --service-weights service_weights.yaml \
           --out-prefix results/report
```

This generates:
- `results/report_scores.json` - Detailed scoring data
- `results/report_analysis.csv` - Tabular analysis
- `results/report_report.html` - Executive report

## Configuration

### Rule Weights (`weights.yaml`)

Map rule IDs to severity weights (1-10 scale recommended):

```yaml
weights:
  # Specific rules
  gws.gmail.1.1: 5    # Critical
  gws.gmail.2.1: 3    # High
  
  # Prefix matching (applies to all rules starting with prefix)
  gws.common.: 3      # All common rules are High
  gws.drive.: 2       # All drive rules are Medium
```

Default weights: Critical=5, High=3, Medium=2, Low=1

### Service Weights (`service_weights.yaml`)

Configure relative importance of services (should sum to 1.0):

```yaml
service_weights:
  gmail: 0.20
  drive: 0.20
  common: 0.20
  groups: 0.10
  chat: 0.10
  meet: 0.05
  calendar: 0.05
  classroom: 0.05
  sites: 0.05
```

### Compensating Controls (`compensating.yaml`)

Document alternative security measures for failed rules:

```yaml
compensating:
  gws.gmail.1.1: "MFA enforced via third-party SSO provider"
  gws.drive.2.1: 
    rationale: "DLP implemented via CASB solution"
    expires: "2024-12-31"
```

Failed rules with compensating controls receive 50% credit.

## Command-Line Options

```bash
scubascore --help
```

### Required Arguments
- `--input, -i`: Path to ScubaGoggles JSON results
- `--out-prefix, -o`: Output file prefix

### Configuration Files
- `--weights, -w`: Rule weight configuration (YAML)
- `--service-weights, -s`: Service importance weights (YAML)
- `--compensating, -c`: Compensating controls (YAML)

### Output Options
- `--formats, -f`: Output formats (default: json csv html)
- `--pretty`: Pretty-print console output

### Other Options
- `--verbose, -v`: Enable debug logging
- `--quiet, -q`: Suppress non-error output
- `--dry-run`: Validate inputs without generating files
- `--strict`: Exit on any parsing errors

## Understanding Scores

### Overall Score
Weighted average of all service scores based on service importance.

### Service Scores
For each service:
- **Score**: Percentage of passed weight vs total evaluated weight
- **Evaluated Weight**: Sum of weights for all PASS/FAIL rules
- **Passed Weight**: Sum of weights for passed rules + 50% of failed rules with compensating controls

### Score Interpretation
- **90-100%**: Excellent security posture
- **80-89%**: Good security posture
- **70-79%**: Fair security posture
- **60-69%**: Poor security posture
- **Below 60%**: Critical security gaps

## Advanced Usage

### Custom Weight Strategies

Create severity-based weights:

```yaml
weights:
  # Critical findings
  gws.common.admin_2fa: 10
  gws.gmail.dmarc_enforcement: 10
  
  # High priority
  gws.drive.external_sharing: 5
  
  # Catch-all by service
  gws.gmail.: 3
  gws.drive.: 3
  gws.: 1  # Everything else is Low
```

### Tracking Improvements

Compare scores over time:

```bash
# January scan
scubascore --input jan_results.json --out-prefix reports/2024-01

# February scan  
scubascore --input feb_results.json --out-prefix reports/2024-02

# Compare JSON outputs to track progress
```

### Integration with CI/CD

```yaml
# .github/workflows/security-check.yml
- name: Run ScubaGoggles
  run: scubagoggles --output results.json

- name: Calculate Security Score
  run: |
    scubascore --input results.json \
               --weights config/weights.yaml \
               --out-prefix reports/security
    
    # Fail if score below threshold
    score=$(jq .overall_score reports/security_scores.json)
    if (( $(echo "$score < 80" | bc -l) )); then
      echo "Security score $score is below threshold of 80"
      exit 1
    fi
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/scubascore.git
cd scubascore

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=scubascore --cov-report=html

# Run specific test file
pytest tests/test_scoring.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black scubascore tests
isort scubascore tests

# Type checking
mypy scubascore

# Linting
flake8 scubascore tests

# Security scan
bandit -r scubascore
```

### Project Structure

```
scubascore/
├── scubascore/           # Main package
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # Command-line interface
│   ├── models.py        # Data models
│   ├── parsers.py       # Input parsing
│   ├── scoring.py       # Score calculation
│   ├── reporters.py     # Output generation
│   ├── validators.py    # Input validation
│   └── exceptions.py    # Custom exceptions
├── tests/               # Test suite
│   ├── fixtures/        # Test data
│   ├── test_*.py        # Test modules
│   └── test_integration.py
├── .github/workflows/   # CI/CD configuration
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
├── setup.py            # Package configuration
└── README.md           # This file
```

## Troubleshooting

### Common Issues

**No rules found in input**
- Check that your JSON file is valid ScubaGoggles output
- Use `--verbose` to see parsing details
- The tool supports multiple JSON structures - ensure your file contains rule data

**Invalid weight configuration**
- Weights must be positive numbers
- YAML syntax must be valid
- Use quotes for rule IDs containing special characters

**Low scores despite compliance**
- Check if N/A rules are affecting denominators
- Verify weight configuration matches your priorities
- Consider documenting compensating controls

### Debug Mode

Run with verbose logging to troubleshoot:

```bash
scubascore --input data.json --out-prefix debug --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`black`)
- Type hints are added
- Documentation is updated

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- CISA for ScubaGoggles
- The security community for best practices
- Contributors and testers

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/scubascore/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/scubascore/discussions)
- Email: scuba@example.com