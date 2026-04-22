"""Ingest skill error classes."""

from __future__ import annotations


class IngestNotFound(Exception):
    """Raised when the requested source artifact cannot be found.

    Examples: fixture file does not exist, upstream API returns 404.
    """


class IngestUnauthorized(Exception):
    """Raised when the caller lacks permission to access the source artifact.

    Examples: upstream API returns 401 or 403.
    """


class IngestMalformed(Exception):
    """Raised when the source payload is structurally invalid or missing required fields.

    Examples: JSON parse error, missing required field, unknown source_type.
    """
