import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


class SyncPublicFilesTest(unittest.TestCase):
    def test_dry_run_and_real_run_copy_only_approved_files(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()

            approved_source = source_root / "approved.docx"
            rejected_source = source_root / "rejected.docx"
            approved_source.write_text("approved", encoding="utf-8")
            rejected_source.write_text("rejected", encoding="utf-8")

            approved = self._candidate(
                approved_source,
                "public/course/approved.docx",
                approved=True,
            )
            rejected = self._candidate(
                rejected_source,
                "public/course/rejected.docx",
                approved=False,
            )
            review_json = self._write_review(repo_root, [approved, rejected])

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                        "--dry-run",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertIn("approved.docx", stdout.getvalue())
            self.assertNotIn("rejected.docx", stdout.getvalue())
            self.assertFalse((repo_root / "public" / "course" / "approved.docx").exists())
            self.assertFalse((repo_root / "public" / "course" / "rejected.docx").exists())
            self.assertFalse((repo_root / "docs" / "review" / "imported-manifest.json").exists())

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(
                (repo_root / "public" / "course" / "approved.docx").read_text(encoding="utf-8"),
                "approved",
            )
            self.assertFalse((repo_root / "public" / "course" / "rejected.docx").exists())

            manifest_path = repo_root / "docs" / "review" / "imported-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest, [approved])

    def test_rejects_traversal_target_without_writing_outside_repo(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()

            source = source_root / "escape.docx"
            source.write_text("escape", encoding="utf-8")
            review_json = self._write_review(
                repo_root,
                [self._candidate(source, "../escape.docx", approved=True)],
            )

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("target path escapes archive root", stderr.getvalue())
            self.assertFalse((tmp_path / "escape.docx").exists())
            self.assertFalse((repo_root / "docs" / "review" / "imported-manifest.json").exists())

    def test_review_json_must_be_inside_repo_root(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()
            source = source_root / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            outside_review = tmp_path / "outside.json"
            outside_review.write_text(
                json.dumps([self._candidate(source, "public/approved.docx", approved=True)]),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        outside_review.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("review JSON path escapes repo root", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "approved.docx").exists())

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        "../outside.json",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("review JSON path escapes repo root", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "approved.docx").exists())

    def test_non_bool_approved_returns_validation_error_without_copying(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()

            source = source_root / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            review_json = self._write_review(
                repo_root,
                [self._candidate(source, "public/approved.docx", approved="true")],
            )

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("approved must be a bool", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "approved.docx").exists())
            self.assertFalse((repo_root / "docs" / "review" / "imported-manifest.json").exists())

    def test_validates_all_approved_targets_before_copying(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()

            safe_source = source_root / "safe.docx"
            unsafe_source = source_root / "unsafe.docx"
            safe_source.write_text("safe", encoding="utf-8")
            unsafe_source.write_text("unsafe", encoding="utf-8")
            review_json = self._write_review(
                repo_root,
                [
                    self._candidate(safe_source, "public/course/safe.docx", approved=True),
                    self._candidate(unsafe_source, "../unsafe.docx", approved=True),
                ],
            )

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("target path escapes archive root", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "course" / "safe.docx").exists())
            self.assertFalse((tmp_path / "unsafe.docx").exists())
            self.assertFalse((repo_root / "docs" / "review" / "imported-manifest.json").exists())

    def _main(self):
        try:
            from scripts.sync_public_files import main
        except ModuleNotFoundError as exc:
            if exc.name == "scripts.sync_public_files":
                self.fail("scripts.sync_public_files module is missing")
            raise
        return main

    def _write_review(self, repo_root, candidates):
        review_json = repo_root / "docs" / "review" / "candidates.json"
        review_json.parent.mkdir(parents=True)
        review_json.write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return review_json

    def _candidate(self, source, target_rel, approved):
        return {
            "source": source.as_posix(),
            "source_rel": source.name,
            "target_rel": target_rel,
            "semester": "fall-2025",
            "course": "course",
            "size": source.stat().st_size,
            "suffix": source.suffix,
            "category": "suggested",
            "reason": "test fixture",
            "approved": approved,
        }


if __name__ == "__main__":
    unittest.main()
