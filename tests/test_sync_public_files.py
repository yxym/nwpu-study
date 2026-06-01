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
            whitelist = self._write_whitelist(repo_root, source_root)

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
                        "--whitelist",
                        whitelist.as_posix(),
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
                        "--whitelist",
                        whitelist.as_posix(),
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
            expected_manifest = dict(approved, source="approved.docx", source_rel="approved.docx")
            self.assertEqual(manifest, [expected_manifest])

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
            whitelist = self._write_whitelist(repo_root, source_root)
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
                        "--whitelist",
                        whitelist.as_posix(),
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
            whitelist = self._write_whitelist(repo_root, source_root)
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
                        "--whitelist",
                        whitelist.as_posix(),
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
                        "--whitelist",
                        whitelist.as_posix(),
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
            whitelist = self._write_whitelist(repo_root, source_root)
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
                        "--whitelist",
                        whitelist.as_posix(),
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
            whitelist = self._write_whitelist(repo_root, source_root)
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
                        "--whitelist",
                        whitelist.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("target path escapes archive root", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "course" / "safe.docx").exists())
            self.assertFalse((tmp_path / "unsafe.docx").exists())
            self.assertFalse((repo_root / "docs" / "review" / "imported-manifest.json").exists())

    def test_relative_sources_are_resolved_against_whitelist_source_root(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            course_dir.mkdir(parents=True)
            repo_root.mkdir()

            source = course_dir / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            whitelist = self._write_whitelist(repo_root, source_root)
            review_json = self._write_review(
                repo_root,
                [
                    self._candidate(
                        "02大二/大二上/材料化学/approved.docx",
                        "public/course/approved.docx",
                        approved=True,
                    )
                ],
            )

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                        "--whitelist",
                        whitelist.as_posix(),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual((repo_root / "public" / "course" / "approved.docx").read_text(), "approved")

    def test_manifest_normalizes_legacy_absolute_sources_to_relative_paths(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            course_dir.mkdir(parents=True)
            repo_root.mkdir()

            source = course_dir / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            whitelist = self._write_whitelist(repo_root, source_root)
            review_json = self._write_review(
                repo_root,
                [self._candidate(source, "public/course/approved.docx", approved=True)],
            )

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                        "--whitelist",
                        whitelist.as_posix(),
                    ]
                )

            self.assertEqual(result, 0)
            manifest_path = repo_root / "docs" / "review" / "imported-manifest.json"
            manifest_text = manifest_path.read_text(encoding="utf-8")
            manifest = json.loads(manifest_text)
            self.assertEqual(manifest[0]["source"], "02大二/大二上/材料化学/approved.docx")
            self.assertEqual(manifest[0]["source_rel"], "02大二/大二上/材料化学/approved.docx")
            self.assertNotIn(source_root.as_posix(), manifest_text)

    def test_rejects_absolute_source_outside_whitelist_source_root(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            outside_root = tmp_path / "outside"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            outside_root.mkdir()
            repo_root.mkdir()

            source = outside_root / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            whitelist = self._write_whitelist(repo_root, source_root)
            review_json = self._write_review(
                repo_root,
                [self._candidate(source, "public/approved.docx", approved=True)],
            )

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                        "--whitelist",
                        whitelist.as_posix(),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("source path escapes source root", stderr.getvalue())
            self.assertFalse((repo_root / "public" / "approved.docx").exists())

    def test_dry_run_prints_only_public_safe_relative_paths(self):
        main = self._main()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            course_dir.mkdir(parents=True)
            repo_root.mkdir()

            source = course_dir / "approved.docx"
            source.write_text("approved", encoding="utf-8")
            whitelist = self._write_whitelist(repo_root, source_root)
            review_json = self._write_review(
                repo_root,
                [
                    self._candidate(
                        "02大二/大二上/材料化学/approved.docx",
                        "public/course/approved.docx",
                        approved=True,
                    )
                ],
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "--repo-root",
                        repo_root.as_posix(),
                        "--review-json",
                        review_json.as_posix(),
                        "--whitelist",
                        whitelist.as_posix(),
                        "--dry-run",
                    ]
                )

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("02大二/大二上/材料化学/approved.docx -> public/course/approved.docx", output)
            self.assertNotIn(tmp_path.as_posix(), output)

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
        source_text = source.as_posix() if isinstance(source, Path) else source
        source_path = Path(source)
        return {
            "source": source_text,
            "source_rel": source_path.name,
            "target_rel": target_rel,
            "semester": "fall-2025",
            "course": "course",
            "size": source.stat().st_size if isinstance(source, Path) else 8,
            "suffix": source_path.suffix,
            "category": "suggested",
            "reason": "test fixture",
            "approved": approved,
        }

    def _write_whitelist(self, repo_root, source_root):
        whitelist = repo_root / "public-whitelist.yml"
        whitelist.write_text(
            json.dumps({"source_root": source_root.as_posix(), "courses": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        return whitelist


if __name__ == "__main__":
    unittest.main()
