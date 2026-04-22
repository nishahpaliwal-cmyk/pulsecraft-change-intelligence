"""Audit skill — thin wrapper over AuditWriter for use in hooks and commands.

Import from here rather than instantiating AuditWriter directly in hooks/commands.
Skills receive the writer as a parameter; no global state.
"""

from __future__ import annotations

from pulsecraft.orchestrator.audit import AuditReader, AuditWriter
from pulsecraft.schemas.audit_record import AuditRecord

__all__ = ["AuditReader", "AuditWriter", "AuditRecord", "write_audit"]


def write_audit(record: AuditRecord, writer: AuditWriter) -> None:
    """Write a single AuditRecord via the provided writer instance."""
    writer.log_event(record)
