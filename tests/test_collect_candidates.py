import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


class CollectCandidatesTest(unittest.TestCase):
    def test_cli_writes_only_whitelisted_unpruned_course_files(self):
        try:
            from scripts.collect_candidates import main
        except ModuleNotFoundError as exc:
            if exc.name == "scripts.collect_candidates":
                self.fail("scripts.collect_candidates module is missing")
            raise

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            private_sibling = source_root / "02大二" / "大二上" / "班级名单"
            pruned_private = course_dir / "case study个人"

            course_dir.mkdir(parents=True)
            private_sibling.mkdir(parents=True)
            pruned_private.mkdir(parents=True)
            repo_root.mkdir()

            (course_dir / "M9 report.docx").write_text("report", encoding="utf-8")
            (course_dir / "Lecture 1.pptx").write_text("lecture", encoding="utf-8")
            (private_sibling / "名单.xlsx").write_text("names", encoding="utf-8")
            (pruned_private / "private.docx").write_text("private", encoding="utf-8")

            whitelist = tmp_path / "public-whitelist.yml"
            output_md = "docs/review/candidates.md"
            output_json = "docs/review/candidates.json"
            whitelist.write_text(
                json.dumps(
                    {
                        "source_root": source_root.as_posix(),
                        "courses": [
                            {
                                "semester": "大二上",
                                "target": "材料化学",
                                "sources": ["02大二/大二上/材料化学"],
                                "include": [],
                                "exclude": [],
                                "prune": ["case study个人/**"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = main(
                [
                    "--whitelist",
                    whitelist.as_posix(),
                    "--repo-root",
                    repo_root.as_posix(),
                    "--output-md",
                    output_md,
                    "--output-json",
                    output_json,
                ]
            )

            self.assertEqual(result, 0)
            output_md_path = repo_root / output_md
            output_json_path = repo_root / output_json
            self.assertTrue(output_md_path.exists())
            self.assertTrue(output_json_path.exists())

            markdown = output_md_path.read_text(encoding="utf-8")
            data = json.loads(output_json_path.read_text(encoding="utf-8"))
            serialized = json.dumps(data, ensure_ascii=False)

            self.assertIn("M9 report.docx", markdown)
            self.assertIn("Lecture 1.pptx", markdown)
            self.assertIn("M9 report.docx", serialized)
            self.assertIn("Lecture 1.pptx", serialized)
            self.assertNotIn("班级名单", markdown)
            self.assertNotIn("case study个人", markdown)
            self.assertNotIn("班级名单", serialized)
            self.assertNotIn("case study个人", serialized)
            self.assertEqual(len(data), 2)

    def test_cli_rejects_output_paths_outside_repo(self):
        from scripts.collect_candidates import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            course_dir.mkdir(parents=True)
            repo_root.mkdir()
            (course_dir / "M9 report.docx").write_text("report", encoding="utf-8")
            whitelist = self._write_whitelist(tmp_path, source_root)

            absolute_md = repo_root / "docs" / "review" / "absolute.md"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--whitelist",
                        whitelist.as_posix(),
                        "--repo-root",
                        repo_root.as_posix(),
                        "--output-md",
                        absolute_md.as_posix(),
                        "--output-json",
                        "docs/review/candidates.json",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("output path must be relative", stderr.getvalue())
            self.assertFalse(absolute_md.exists())
            self.assertFalse((repo_root / "docs" / "review" / "candidates.json").exists())

            escaping_md = tmp_path / "escaping.md"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--whitelist",
                        whitelist.as_posix(),
                        "--repo-root",
                        repo_root.as_posix(),
                        "--output-md",
                        "../escaping.md",
                        "--output-json",
                        "docs/review/candidates.json",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("output path escapes repo root", stderr.getvalue())
            self.assertFalse(escaping_md.exists())
            self.assertFalse((repo_root / "docs" / "review" / "candidates.json").exists())

            escaping_json = tmp_path / "escaping.json"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "--whitelist",
                        whitelist.as_posix(),
                        "--repo-root",
                        repo_root.as_posix(),
                        "--output-md",
                        "docs/review/candidates.md",
                        "--output-json",
                        "../escaping.json",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("output path escapes repo root", stderr.getvalue())
            self.assertFalse((repo_root / "docs" / "review" / "candidates.md").exists())
            self.assertFalse(escaping_json.exists())

    def test_markdown_escapes_pipe_in_file_paths(self):
        from scripts.collect_candidates import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            course_dir = source_root / "02大二" / "大二上" / "材料化学"
            course_dir.mkdir(parents=True)
            repo_root.mkdir()
            (course_dir / "A|B report.docx").write_text("report", encoding="utf-8")
            whitelist = self._write_whitelist(tmp_path, source_root)

            result = main(
                [
                    "--whitelist",
                    whitelist.as_posix(),
                    "--repo-root",
                    repo_root.as_posix(),
                    "--output-md",
                    "docs/review/candidates.md",
                    "--output-json",
                    "docs/review/candidates.json",
                ]
            )

            self.assertEqual(result, 0)
            markdown = (repo_root / "docs" / "review" / "candidates.md").read_text(encoding="utf-8")
            self.assertIn("A\\|B report.docx", markdown)
            self.assertNotIn("A|B report.docx", markdown)

    def test_cli_reports_missing_sources_without_writing_outputs(self):
        from scripts.collect_candidates import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            repo_root = tmp_path / "repo"
            source_root.mkdir()
            repo_root.mkdir()
            whitelist = self._write_whitelist(tmp_path, source_root)
            output_md = repo_root / "docs" / "review" / "candidates.md"
            output_json = repo_root / "docs" / "review" / "candidates.json"
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                result = main(
                    [
                        "--whitelist",
                        whitelist.as_posix(),
                        "--repo-root",
                        repo_root.as_posix(),
                        "--output-md",
                        "docs/review/candidates.md",
                        "--output-json",
                        "docs/review/candidates.json",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("02大二/大二上/材料化学", stderr.getvalue())
            self.assertFalse(output_md.exists())
            self.assertFalse(output_json.exists())

    def _write_whitelist(self, tmp_path, source_root):
        whitelist = tmp_path / "public-whitelist.yml"
        whitelist.write_text(
            json.dumps(
                {
                    "source_root": source_root.as_posix(),
                    "courses": [
                        {
                            "semester": "大二上",
                            "target": "材料化学",
                            "sources": ["02大二/大二上/材料化学"],
                            "include": [],
                            "exclude": [],
                            "prune": ["case study个人/**"],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return whitelist


if __name__ == "__main__":
    unittest.main()
