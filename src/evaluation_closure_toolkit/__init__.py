"""Offline analysis of supplied evaluation dossiers, under explicit scope."""

__version__ = "0.1.0.dev1"

from .api import analyze_bytes, validate_bytes
from .errors import AdmissionError, InternalError, ReportError, RequestError
from .reporting import render_markdown

__all__ = [
    "analyze_bytes", "validate_bytes", "render_markdown", "__version__",
    "AdmissionError", "InternalError", "ReportError", "RequestError",
]
