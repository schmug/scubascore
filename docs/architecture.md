# SCuBA Scoring Kit - Architecture

## Overview

The SCuBA Scoring Kit is designed as a modular Python application that processes security assessment data from CISA ScubaGoggles and generates weighted security scores. The architecture emphasizes extensibility, maintainability, and reliability.

## Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Type Safety**: Extensive use of type hints and data classes
3. **Schema Tolerance**: Flexible parsing to handle various input formats
4. **Fail-Safe**: Graceful error handling with informative messages
5. **Extensibility**: Easy to add new features without modifying core logic

## Module Structure

```
scubascore/
├── __init__.py      # Package initialization and exports
├── cli.py           # Command-line interface
├── models.py        # Data models and structures
├── parsers.py       # Input parsing and loading
├── scoring.py       # Score calculation engine
├── reporters.py     # Output generation
├── validators.py    # Input validation
└── exceptions.py    # Custom exceptions
```

### Module Responsibilities

#### models.py
- Defines all data structures using dataclasses
- Provides type-safe representations of rules, scores, and configurations
- Implements business logic methods on data models

Key Classes:
- `Rule`: Represents a security rule with verdict and metadata
- `ServiceScore`: Tracks scoring for a specific service
- `ScoreResult`: Complete scoring results
- `WeightConfig`: Rule weight configuration
- `ServiceWeightConfig`: Service importance weights
- `CompensatingControlConfig`: Compensating control definitions

#### parsers.py
- Handles all input file loading and parsing
- Implements schema-tolerant JSON parsing
- Loads and validates YAML configurations
- Normalizes various input formats to standard models

Key Functions:
- `load_json_flexible()`: Robust JSON loading
- `parse_scuba_results()`: Extract rules from ScubaGoggles output
- `load_weight_config()`: Load rule weight configuration
- `iter_rules_from_json()`: Generator for efficient rule extraction

#### scoring.py
- Implements the core scoring algorithm
- Calculates per-service and overall scores
- Handles compensating controls
- Provides scoring statistics and summaries

Key Functions:
- `compute_scores()`: Main scoring engine
- `calculate_overall_score()`: Weighted average calculation
- `get_failed_rules_by_severity()`: Group failures by severity
- `get_score_summary()`: Generate summary statistics

#### reporters.py
- Generates output in multiple formats
- Handles all file writing operations
- Formats data for different audiences
- Ensures output consistency

Key Functions:
- `generate_reports()`: Main report generation interface
- `write_json_report()`: Detailed JSON output
- `write_csv_report()`: Tabular analysis
- `write_html_report()`: Executive-friendly report
- `write_markdown_report()`: Documentation-friendly format

#### validators.py
- Validates all inputs before processing
- Provides helpful error messages
- Checks configuration consistency
- Ensures data integrity

Key Functions:
- `validate_json_structure()`: Check JSON has expected format
- `validate_rule_entry()`: Validate individual rules
- `validate_weight_config()`: Ensure weights are valid
- `validate_cli_args()`: Comprehensive CLI validation

#### cli.py
- Implements the command-line interface
- Handles argument parsing and validation
- Orchestrates the processing pipeline
- Manages output and logging

Key Functions:
- `create_parser()`: Build argument parser
- `validate_args()`: Validate CLI arguments
- `print_summary()`: Display results summary
- `main()`: Entry point and orchestration

#### exceptions.py
- Defines custom exception hierarchy
- Provides specific error types
- Enables precise error handling

Exception Hierarchy:
```
ScubaScoreError (base)
├── ParsingError
├── ConfigurationError
├── ScoringError
└── ReportingError
```

## Data Flow

```
1. CLI Input
   ↓
2. Validation (validators.py)
   ↓
3. File Loading (parsers.py)
   ↓
4. Data Parsing (parsers.py)
   ↓
5. Score Calculation (scoring.py)
   ↓
6. Report Generation (reporters.py)
   ↓
7. Output Files
```

## Key Design Patterns

### 1. Builder Pattern
Used in report generation to construct complex outputs step by step.

### 2. Strategy Pattern
Different parsing strategies for various JSON structures.

### 3. Factory Pattern
Model creation with validation and defaults.

### 4. Generator Pattern
Memory-efficient iteration over large rule sets.

## Configuration System

The application uses a three-tier configuration system:

1. **Default Values**: Built into the code
2. **Configuration Files**: YAML files for weights and controls
3. **Command-Line Arguments**: Override any setting

Priority: CLI args > Config files > Defaults

## Error Handling Strategy

1. **Validation First**: Check inputs before processing
2. **Specific Exceptions**: Use custom exceptions for different error types
3. **Graceful Degradation**: Continue processing valid data when possible
4. **Informative Messages**: Include context and suggestions in errors
5. **Logging Levels**: Debug, info, warning, error for different scenarios

## Extension Points

The architecture provides several extension points for future enhancements:

1. **New Input Formats**: Add parsers for different security tools
2. **Scoring Algorithms**: Implement alternative scoring methods
3. **Output Formats**: Add new report types (PDF, Excel, etc.)
4. **Data Sources**: Support for APIs, databases, etc.
5. **Validation Rules**: Add custom validation logic
6. **Plugins**: Hook system for third-party extensions

## Performance Considerations

1. **Lazy Loading**: Use generators for large datasets
2. **Compiled Patterns**: Regex patterns compiled once
3. **Efficient Data Structures**: Dataclasses over dictionaries
4. **Streaming**: Process rules without loading all into memory
5. **Caching**: Ready for caching layer if needed

## Security Considerations

1. **Input Validation**: All inputs validated before use
2. **Path Traversal**: File paths validated
3. **HTML Escaping**: Prevent XSS in HTML reports
4. **No Hardcoded Secrets**: All configuration externalized
5. **Minimal Permissions**: No elevated privileges required

## Testing Strategy

1. **Unit Tests**: Each module tested independently
2. **Integration Tests**: End-to-end workflow tests
3. **Fixtures**: Sample data for various scenarios
4. **Mocking**: External dependencies mocked
5. **Coverage**: Aim for >90% code coverage

## Future Architecture Considerations

### Microservices
The modular design allows easy transition to microservices:
- Parsing service
- Scoring service
- Reporting service

### API Layer
RESTful API can be added on top:
```python
from flask import Flask
from scubascore import parse_scuba_results, compute_scores

app = Flask(__name__)

@app.route('/score', methods=['POST'])
def score():
    # Use existing modules
    pass
```

### Database Integration
Models are ready for ORM mapping:
```python
# Future: SQLAlchemy models
class RuleDB(Base):
    __tablename__ = 'rules'
    # Map from Rule dataclass
```

This architecture provides a solid foundation for growth while maintaining simplicity for current use cases.