import hashlib
import tempfile
import unittest
from pathlib import Path

from integrity import compare, external_baseline, snapshot, validate


class IntegrityTests(unittest.TestCase):
    def test_changes_are_classified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "same.txt").write_text("same")
            (root / "changed.txt").write_text("before")
            (root / "removed.txt").write_text("old")
            baseline = snapshot(root)
            (root / "changed.txt").write_text("after")
            (root / "removed.txt").unlink()
            (root / "added.txt").write_text("new")
            result = compare(baseline, snapshot(root))
            self.assertEqual(result["modified"], ["changed.txt"])
            self.assertEqual(result["removed"], ["removed.txt"])
            self.assertEqual(result["added"], ["added.txt"])
            self.assertTrue(result["changed"])

    def test_nested_binary_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            data = bytes(range(256)) * 5000
            (root / "nested" / "data.bin").write_bytes(data)
            self.assertEqual(snapshot(root)["files"]["nested/data.bin"], hashlib.sha256(data).hexdigest())

    def test_unchanged_and_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            current = snapshot(Path(directory))
            self.assertFalse(compare(current, current)["changed"])

    def test_symlinks_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target").write_text("content")
            try:
                (root / "link").symlink_to(root / "target")
            except OSError:
                self.skipTest("symlinks unavailable")
            current = snapshot(root)
            self.assertEqual(current["skipped_symlinks"], ["link"])
            self.assertNotIn("link", current["files"])

    def test_directory_symlink_not_traversed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "secret").write_text("outside")
            try:
                (Path(directory) / "link").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            self.assertEqual(snapshot(Path(directory))["files"], {})

    def test_missing_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                snapshot(Path(directory) / "missing")

    def test_file_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file"
            path.touch()
            with self.assertRaises(ValueError):
                snapshot(path)

    def test_invalid_baselines(self):
        invalid = [[], {}, {"version": 2, "algorithm": "sha256", "files": {}},
                   {"version": 1, "algorithm": "sha256", "files": []},
                   {"version": 1, "algorithm": "sha256", "files": {"a": "bad"}},
                   {"version": 1, "algorithm": "sha256", "files": {"../a": "0" * 64}}]
        for baseline in invalid:
            with self.subTest(baseline=baseline), self.assertRaises(ValueError):
                validate(baseline)

    def test_baseline_must_be_external(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                external_baseline(root, root / "baseline.json")
            external_baseline(root, root.parent / "baseline.json")


if __name__ == "__main__":
    unittest.main()
