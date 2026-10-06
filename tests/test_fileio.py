"""Counterexamples for explicit file ownership, refusal and bounded capture."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluation_closure_toolkit import fileio


class FileBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "dossier.json"
        self.source.write_bytes(b"{\"payload\":\"private\"}\n")

    def test_exact_regular_file_bytes_and_single_open(self):
        original = os.open
        with patch.object(fileio.os, "open", wraps=original) as opened:
            result = fileio.read_input(self.source)
        self.assertEqual(result, b"{\"payload\":\"private\"}\n")
        self.assertEqual(opened.call_count, 1)

    def test_exclusive_output_and_input_collision_preserve_existing_bytes(self):
        output = self.root / "report.json"
        fileio.write_output(output, b"new report\n")
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(output, b"replacement")
        self.assertEqual(output.read_bytes(), b"new report\n")
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(self.source, b"replacement")
        self.assertIn(b"private", self.source.read_bytes())
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_refuses_directories_missing_parents_and_parent_traversal(self):
        for path in (self.root, self.root / "missing.json", self.root / ".." / "dossier.json", "-"):
            with self.subTest(path=str(path)):
                with self.assertRaises(fileio.FileBoundaryError) as context:
                    fileio.read_input(path)
                self.assertNotIn(str(self.root), str(context.exception))
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(self.root / "new-directory" / "report.json", b"x")
        self.assertFalse((self.root / "new-directory").exists())
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(self.root / ".." / "report.json", b"x")

    def _symlink(self, target, link, *, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is unavailable on this host")

    def test_refuses_leaf_links_and_broken_output_links(self):
        link = self.root / "linked.json"
        self._symlink(self.source, link)
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.read_input(link)
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(link, b"overwrite")
        broken = self.root / "broken.json"
        self._symlink(self.root / "does-not-exist", broken)
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(broken, b"overwrite")
        self.assertTrue(broken.is_symlink())

    def test_refuses_linked_parent_components(self):
        actual = self.root / "real"
        actual.mkdir()
        (actual / "input.json").write_bytes(b"{}")
        linked = self.root / "link"
        self._symlink(actual, linked, directory=True)
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.read_input(linked / "input.json")
        with self.assertRaises(fileio.FileBoundaryError):
            fileio.write_output(linked / "output.json", b"x")
        self.assertFalse((actual / "output.json").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unsupported")
    def test_fifo_refused_before_open_can_block(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        with patch.object(fileio.os, "open", side_effect=AssertionError("must not open FIFO")):
            with self.assertRaises(fileio.FileBoundaryError):
                fileio.read_input(fifo)

    def test_windows_reparse_flag_is_refused_even_without_symlink_mode(self):
        info = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
        self.assertTrue(fileio._is_link(info))

    def test_descriptor_is_checked_as_regular(self):
        with patch.object(fileio.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFIFO)):
            with self.assertRaises(fileio.FileBoundaryError):
                fileio.read_input(self.source)

    def test_byte_limit_refuses_incomplete_capture_without_returning_a_hash(self):
        self.source.write_bytes(b"1234")
        with patch.object(fileio, "MAX_INPUT_BYTES", 3):
            with self.assertRaises(fileio.InputLimitError) as context:
                fileio.read_input(self.source)
        self.assertEqual(str(context.exception), "INPUT_BYTE_LIMIT")
        self.source.write_bytes(b"123")
        with patch.object(fileio, "MAX_INPUT_BYTES", 3):
            self.assertEqual(fileio.read_input(self.source), b"123")

    def test_partial_write_removes_only_new_incomplete_output(self):
        output = self.root / "partial.json"
        original = os.write
        calls = 0

        def interrupted(descriptor, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(descriptor, data[:2])
            raise OSError("private-path-and-payload")

        with patch.object(fileio.os, "write", side_effect=interrupted):
            with self.assertRaises(fileio.FileBoundaryError) as context:
                fileio.write_output(output, b"abcdef")
        self.assertEqual(str(context.exception), "IO_OUTPUT_FAILED")
        self.assertFalse(output.exists())
        self.assertTrue(self.source.exists())

    @unittest.skipIf(os.name == "nt", "Windows does not permit replacement of this open file")
    def test_cleanup_does_not_delete_a_replacement_file(self):
        output = self.root / "replacement.json"

        def replace_then_fail(descriptor, data):
            output.unlink()
            output.write_bytes(b"replacement belongs to someone else")
            raise OSError("write interrupted")

        with patch.object(fileio.os, "write", side_effect=replace_then_fail):
            with self.assertRaises(fileio.FileBoundaryError):
                fileio.write_output(output, b"original")
        self.assertEqual(output.read_bytes(), b"replacement belongs to someone else")


if __name__ == "__main__":
    unittest.main()
