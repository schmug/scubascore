# Release Notes - v1.0.0

## 🎉 Major Release: Modular Architecture

We're excited to announce the release of SCuBA Scoring Kit v1.0.0! This release represents a complete refactoring of the codebase from a monolithic script to a professional, modular Python package.

### 🚀 Highlights

- **Professional Package Structure**: Properly organized Python package with clear separation of concerns
- **Enhanced Reliability**: Comprehensive input validation and error handling
- **Better Developer Experience**: Full type hints, comprehensive tests, and modern tooling
- **Improved CLI**: Enhanced command-line interface with helpful options
- **Multiple Output Formats**: Now supports Markdown in addition to JSON, CSV, and HTML

### 💥 Breaking Changes

- The tool must now be installed using `pip install`
- The main command is now `scubascore` instead of `python scubascore.py`
- Some output file names have changed:
  - `_scores.csv` → `_analysis.csv`
  - `_summary.html` → `_report.html`

### 🆕 New Features

- **Modular Architecture**: Clean separation into parsers, models, scoring, and reporting modules
- **Type Safety**: Complete type annotations throughout the codebase
- **Input Validation**: Comprehensive validation with helpful error messages
- **Dry Run Mode**: Validate inputs without generating output files
- **Verbosity Control**: `--verbose` and `--quiet` options
- **Better Error Messages**: Detailed context and suggestions for fixing issues
- **Markdown Reports**: New output format for documentation
- **CI/CD Pipeline**: Automated testing with GitHub Actions

### 🔧 Improvements

- Schema-tolerant parsing handles more ScubaGoggles output variations
- Better service inference from rule IDs
- Improved weight configuration with prefix matching
- Enhanced HTML reports with better styling
- Comprehensive test coverage
- Professional documentation

### 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/scubascore.git
cd scubascore

# Install the package
pip install -e .

# Or install from PyPI (when published)
pip install scubascore
```

### 🔄 Migration

See the [Migration Guide](migration-guide.md) for detailed instructions on upgrading from v0.x.

Quick migration:
```bash
# Old
python scubascore.py --input data.json --weights weights.yaml --out-prefix output

# New
scubascore --input data.json --weights weights.yaml --out-prefix output
```

### 📚 Documentation

- [README](../README.md) - Getting started and usage
- [Migration Guide](migration-guide.md) - Upgrading from v0.x
- [Architecture](architecture.md) - Technical design and structure
- [CHANGELOG](../CHANGELOG.md) - Detailed change history

### 🙏 Acknowledgments

Thanks to all contributors and users who provided feedback for this major release. Special thanks to the CISA team for ScubaGoggles.

### 📈 What's Next

Future releases will focus on:
- Additional output formats (PDF, Excel)
- API/Web service mode
- Enhanced reporting features
- Performance optimizations
- Plugin system for extensions

### 🐛 Bug Reports

Please report any issues on our [GitHub Issues](https://github.com/yourusername/scubascore/issues) page.

---

**Full Changelog**: [v0.1.0...v1.0.0](https://github.com/yourusername/scubascore/compare/v0.1.0...v1.0.0)