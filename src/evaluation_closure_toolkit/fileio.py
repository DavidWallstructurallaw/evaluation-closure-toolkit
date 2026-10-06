"""Bounded, explicit local file I/O for the command-line boundary.

All path components are checked for links and Windows reparse points. Descriptor
checks and no-follow flags supplement those checks where available. This protects
against untrusted dossiers in a caller-controlled directory; it does not claim
protection against a concurrent local process replacing directory components.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

MAX_INPUT_BYTES = 10 * 1024 * 1024


class FileBoundaryError(OSError):
    """A sanitized filesystem diagnostic containing no supplied path."""


class InputLimitError(ValueError):
    """The file exceeded the read limit before complete capture."""


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _path(value: str | os.PathLike[str], code: str) -> Path:
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or not raw or raw == "-" or "\x00" in raw:
            raise FileBoundaryError(code)
        candidate = Path(raw)
        if ".." in candidate.parts:
            raise FileBoundaryError(code)
        # abspath is lexical, unlike resolve(), and does not follow links.
        return Path(os.path.abspath(candidate))
    except (TypeError, ValueError, OSError):
        raise FileBoundaryError(code) from None


def _ordinary_components(path: Path, *, include_file: bool, code: str) -> None:
    parts = path.parts
    current = Path(parts[0])
    end = len(parts) if include_file else len(parts) - 1
    try:
        root = os.lstat(current)
        if _is_link(root) or not stat.S_ISDIR(root.st_mode):
            raise FileBoundaryError(code)
        for index in range(1, end):
            current = current / parts[index]
            info = os.lstat(current)
            if _is_link(info):
                raise FileBoundaryError(code)
            if index < len(parts) - 1 or not include_file:
                if not stat.S_ISDIR(info.st_mode):
                    raise FileBoundaryError(code)
            elif not stat.S_ISREG(info.st_mode):
                raise FileBoundaryError(code)
    except (OSError, ValueError):
        raise FileBoundaryError(code) from None


def read_input(path: str | os.PathLike[str]) -> bytes:
    """Read one regular file once, refusing links and oversize capture.

An oversized file receives no input hash: the bounded prefix is not its complete
identity. Byte API callers that already hold complete bytes use admission errors.
"""
    checked = _path(path, "IO_INPUT_REFUSED")
    _ordinary_components(checked, include_file=True, code="IO_INPUT_REFUSED")
    descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(checked, flags)
        info = os.fstat(descriptor)
        if _is_link(info) or not stat.S_ISREG(info.st_mode):
            raise FileBoundaryError("IO_INPUT_REFUSED")
        chunks = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        captured = b"".join(chunks)
        if len(captured) > MAX_INPUT_BYTES:
            raise InputLimitError("INPUT_BYTE_LIMIT")
        return captured
    except (FileBoundaryError, InputLimitError):
        raise
    except (OSError, ValueError):
        raise FileBoundaryError("IO_INPUT_FAILED") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _remove_owned_incomplete(path: Path, identity: os.stat_result) -> None:
    """Remove only the regular file created by this invocation, if still present."""
    try:
        current = os.lstat(path)
        if (
            not _is_link(current)
            and stat.S_ISREG(current.st_mode)
            and (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)
        ):
            os.unlink(path)
    except OSError:
        pass


def write_output(path: str | os.PathLike[str], content: bytes) -> None:
    """Create a private new regular file, never replacing a preexisting path."""
    checked = _path(path, "IO_OUTPUT_REFUSED")
    _ordinary_components(checked, include_file=False, code="IO_OUTPUT_REFUSED")
    descriptor = None
    identity = None
    completed = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(checked, flags, 0o600)
        except FileExistsError:
            raise FileBoundaryError("IO_OUTPUT_REFUSED") from None
        identity = os.fstat(descriptor)
        if _is_link(identity) or not stat.S_ISREG(identity.st_mode):
            raise FileBoundaryError("IO_OUTPUT_REFUSED")
        remaining = memoryview(content)
        while remaining:
            count = os.write(descriptor, remaining)
            if count <= 0:
                raise FileBoundaryError("IO_OUTPUT_FAILED")
            remaining = remaining[count:]
        os.close(descriptor)
        descriptor = None
        completed = True
    except FileBoundaryError:
        raise
    except (OSError, ValueError):
        raise FileBoundaryError("IO_OUTPUT_FAILED") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if not completed and identity is not None:
            _remove_owned_incomplete(checked, identity)
