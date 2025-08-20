# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-20

### Added
- Complete modular architecture with separate modules for parsing, scoring, and reporting
- Type hints throughout the codebase for better IDE support
- Comprehensive input validation with helpful error messages
- Custom exception hierarchy for better error handling
- Structured logging support
- Unit and integration test suite
- CI/CD pipeline with GitHub Actions
- Support for Markdown report format
- Dry-run mode for validation without file generation
- Verbose and quiet modes for output control
- Pretty-print option for console output
- Comprehensive documentation and examples

### Changed
- **BREAKING**: Refactored from monolithic script to Python package
- **BREAKING**: Main entry point is now `scubascore` command after installation
- Improved error messages and validation warnings
- Enhanced CLI with better argument parsing and help text
- Reorganized repository structure with proper Python package layout
- Configuration files moved to `examples/sample_configs/`

### Fixed
- Schema-tolerant parsing now handles more ScubaGoggles output variations
- Better handling of missing or invalid rule entries
- Improved service inference from rule IDs

### Security
- Added HTML output sanitization to prevent XSS
- Input path validation to prevent directory traversal
- Removed hardcoded values in favor of configuration

## [0.1.0] - 2024-01-15

### Initial Release
- Basic SCuBA scoring functionality
- Support for ScubaGoggles JSON input
- Weight-based scoring system
- Compensating controls support
- JSON, CSV, and HTML output formats
- Service-based score aggregation