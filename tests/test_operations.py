import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.operations import apply_operations, safe_target


class OperationTests(unittest.TestCase):
    def test_write_and_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apply_operations(root, [{"type": "write", "path": "a.txt", "content": "alpha"}])
            apply_operations(root, [{"type": "replace", "path": "a.txt", "old": "alpha", "new": "omega"}])
            self.assertEqual((root / "a.txt").read_text(), "omega")

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                safe_target(Path(directory), "../outside.txt")


if __name__ == "__main__":
    unittest.main()
