"""Custom exceptions for claudexml."""


class ClaudeXMLError(Exception):
    """Base exception for claudexml."""


class ParseError(ClaudeXMLError):
    """Raised when XML parsing fails."""

    def __init__(self, message: str, raw_xml: str | None = None) -> None:
        self.raw_xml = raw_xml
        super().__init__(message)


class ValidationError(ClaudeXMLError):
    """Raised when field validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")


class TagNotFoundError(ClaudeXMLError):
    """Raised when a required XML tag is not found."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        super().__init__(f"Required tag <{tag}> not found in XML")
