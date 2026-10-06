"""Public exceptions with payload-free diagnostics."""


class AdmissionError(ValueError):
    """An input cannot be admitted under the closed dossier contract."""

    def __init__(self, code: str, pointer: str = "") -> None:
        self.code = code
        self.pointer = pointer
        super().__init__(code)


class RequestError(ValueError):
    """A requested selection cannot be executed."""


class ReportError(ValueError):
    """A report is outside the supported generated-report contract."""


class InternalError(RuntimeError):
    """An unexpected engine error, without input or machine details."""
