"""Custom exceptions for SCuBA Scoring Kit."""


class ScubaScoreError(Exception):
    """Base exception for all SCuBA Score errors."""
    pass


class ParsingError(ScubaScoreError):
    """Raised when input data cannot be parsed."""
    pass


class ConfigurationError(ScubaScoreError):
    """Raised when configuration is invalid."""
    pass


class ScoringError(ScubaScoreError):
    """Raised when scoring calculation fails."""
    pass


class ReportingError(ScubaScoreError):
    """Raised when report generation fails."""
    pass