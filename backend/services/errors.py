"""
Centralised error types for service-layer validation.

Why this exists:
- Routes (web UI) and CLI tools should not crash with generic ValueError/KeyError.
- Typed exceptions allow clean user-facing messages and consistent test assertions.
- Keeping them in one place avoids circular imports and makes codebase easier to maintain.
"""


class DirectedEvolutionPortalError(Exception):
    """Base class for domain-specific errors in the portal services."""


class FastaParseError(DirectedEvolutionPortalError):
    """Raised when a FASTA file cannot be parsed into valid records."""


class InvalidSequenceError(DirectedEvolutionPortalError):
    """Raised when a parsed sequence contains invalid characters or is empty."""


class UniProtFetchError(DirectedEvolutionPortalError):
    """Raised when UniProt retrieval fails (invalid accession, timeout, etc.)."""
