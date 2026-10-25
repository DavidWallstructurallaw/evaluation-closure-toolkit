"""Offline validate, analyze and installed synthetic-demo entry points."""

from __future__ import annotations

import argparse
import sys
from importlib import resources

from . import __version__
from .errors import RequestError
from .fileio import FileBoundaryError, InputLimitError, read_input, write_output

DEMOS = (
    "incomplete-regression",
    "supported-narrow-regression",
    "scope-mismatch",
    "open-claim-lint",
    "growing-catalog",
    "matched-cohort",
    "recut-comparison",
)
_REQUEST_CODES = {
    "USAGE_INVALID_REQUEST",
    "USAGE_UNKNOWN_REQUEST",
    "USAGE_DUPLICATE_REQUEST",
    "USAGE_SELECTION_LIMIT",
    "USAGE_NO_REQUESTS",
}


class _UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's original message can include arbitrary supplied paths/values.
        raise _UsageError("USAGE_ARGUMENTS")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="evaluation-closure",
        description="Inspect supplied evaluation dossiers offline. Development P1-2: validation, claim lint, structural profiles and compatible comparison.",
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"evaluation-closure {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, explanation in (
        ("validate", "Check dossier syntax, schema and references."),
        ("analyze", "Execute selected dossier requests. Implements lint, profile and compare; later operations remain unsupported."),
        ("demo", "Analyze one installed synthetic example."),
    ):
        sub = commands.add_parser(name, help=explanation, description=explanation, allow_abbrev=False)
        if name == "demo":
            sub.add_argument("name", help="Available: " + ", ".join(DEMOS))
        else:
            sub.add_argument("dossier", help="Explicit regular JSON file; no stdin, links or archives.")
        if name == "analyze":
            sub.add_argument("--request", action="append", metavar="ID", help="Select exact request ID; repeatable.")
        sub.add_argument("--format", choices=("json", "markdown"), default="json")
        sub.add_argument("--output", metavar="NEW_FILE", help="Exclusive new output file; stdout when omitted.")
    return parser


def _exit_status(report: dict) -> int:
    if report.get("admission") == "invalid":
        return 2
    if report.get("execution") == "failed":
        return 1
    if report.get("execution") in {"partial", "not_run"}:
        return 3
    return 0


def _emit_error(code: str) -> None:
    try:
        sys.stderr.write(f"evaluation-closure: {code}\n")
    except (OSError, UnicodeError, ValueError):
        pass


def _stdout(content: bytes) -> None:
    try:
        if hasattr(sys.stdout, "buffer"):
            written = sys.stdout.buffer.write(content)
            if written is not None and written != len(content):
                raise OSError
            sys.stdout.buffer.flush()
        else:
            text = content.decode("utf-8")
            written = sys.stdout.write(text)
            if written is not None and written != len(text):
                raise OSError
            sys.stdout.flush()
    except BrokenPipeError:
        # Prevent a second failing buffered flush at interpreter shutdown from
        # printing a traceback or replacing the documented failure exit code.
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        raise FileBoundaryError("IO_OUTPUT_FAILED") from None
    except (OSError, UnicodeError, ValueError):
        raise FileBoundaryError("IO_OUTPUT_FAILED") from None


def main(argv: list[str] | None = None) -> int:
    """Run the CLI with sanitized errors and the contract's four exit classes."""
    try:
        args = _parser().parse_args(argv)
        # Import after parsing so help/version never loads or analyzes a dossier.
        from . import analyze_bytes, render_markdown, validate_bytes
        from .reporting import canonical_json

        if args.command == "demo":
            if args.name not in DEMOS:
                raise _UsageError("USAGE_UNKNOWN_DEMO")
            try:
                data = resources.files("evaluation_closure_toolkit").joinpath("data", f"{args.name}.json").read_bytes()
            except (OSError, ValueError):
                raise FileBoundaryError("IO_DEMO_UNAVAILABLE") from None
            report = analyze_bytes(data)
        else:
            data = read_input(args.dossier)
            if args.command == "validate":
                report = validate_bytes(data)
            else:
                selected = tuple(args.request) if args.request is not None else None
                report = analyze_bytes(data, request_ids=selected)
        content = canonical_json(report) if args.format == "json" else render_markdown(report).encode("utf-8")
        # All analysis/rendering is complete before exclusive output creation.
        if args.output is None:
            _stdout(content)
        else:
            write_output(args.output, content)
        return _exit_status(report)
    except _UsageError as exc:
        _emit_error(str(exc))
        return 2
    except RequestError as exc:
        code = str(exc)
        _emit_error(code if code in _REQUEST_CODES else "USAGE_INVALID_REQUEST")
        return 2
    except InputLimitError:
        _emit_error("INPUT_BYTE_LIMIT")
        return 2
    except FileBoundaryError as exc:
        code = str(exc)
        allowed = {"IO_INPUT_REFUSED", "IO_INPUT_FAILED", "IO_OUTPUT_REFUSED", "IO_OUTPUT_FAILED", "IO_DEMO_UNAVAILABLE"}
        _emit_error(code if code in allowed else "IO_FAILED")
        return 1
    except (Exception, KeyboardInterrupt):
        _emit_error("INTERNAL_ERROR")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
