import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.build_manifest import main


class BuildManifestTest(unittest.TestCase):
    def test_builds_index_for_whitelisted_course_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "大二上" / "材料化学").mkdir(parents=True)
            (repo / "大二上" / "材料化学" / "report.docx").write_text("x", encoding="utf-8")
            whitelist = repo / "public-whitelist.yml"
            self._write_whitelist(whitelist)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["--repo-root", str(repo), "--whitelist", str(whitelist)])

            self.assertEqual(code, 0)
            self.assertIn("课程数：1", stdout.getvalue())
            index = (repo / "收录内容.md").read_text(encoding="utf-8")
            manifest = json.loads((repo / "docs" / "review" / "repo-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("材料化学", index)
            self.assertEqual(manifest[0]["files"][0]["path"], "大二上/材料化学/report.docx")

    def test_fails_when_imported_path_contains_excluded_keyword(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "大二上" / "材料化学" / "学姐资料").mkdir(parents=True)
            (repo / "大二上" / "材料化学" / "学姐资料" / "old.docx").write_text("x", encoding="utf-8")
            whitelist = repo / "public-whitelist.yml"
            self._write_whitelist(whitelist)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--repo-root", str(repo), "--whitelist", str(whitelist), "--check"])

            self.assertEqual(code, 2)
            self.assertIn("课程数：1", stdout.getvalue())
            self.assertIn("学姐资料/old.docx", stderr.getvalue())

    def test_missing_whitelist_returns_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            missing = repo / "missing.yml"

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["--repo-root", str(repo), "--whitelist", str(missing)])

            self.assertEqual(code, 2)
            self.assertIn("whitelist not found", stderr.getvalue())
            self.assertFalse((repo / "收录内容.md").exists())
            self.assertFalse((repo / "docs" / "review" / "repo-manifest.json").exists())

    def test_skips_non_whitelisted_course_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "大二上" / "材料化学").mkdir(parents=True)
            (repo / "大二上" / "材料化学" / "report.docx").write_text("x", encoding="utf-8")
            (repo / "大二上" / "非白名单课程").mkdir(parents=True)
            (repo / "大二上" / "非白名单课程" / "secret.docx").write_text("x", encoding="utf-8")
            whitelist = repo / "public-whitelist.yml"
            self._write_whitelist(whitelist)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["--repo-root", str(repo), "--whitelist", str(whitelist)])

            self.assertEqual(code, 0)
            self.assertIn("课程数：1", stdout.getvalue())
            index = (repo / "收录内容.md").read_text(encoding="utf-8")
            manifest = json.loads((repo / "docs" / "review" / "repo-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("非白名单课程", index)
            self.assertEqual(len(manifest), 1)
            self.assertEqual(
                [file["path"] for course in manifest for file in course["files"]],
                ["大二上/材料化学/report.docx"],
            )

    def _write_whitelist(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "source_root": "/tmp/source",
                    "courses": [
                        {
                            "semester": "大二上",
                            "target": "材料化学",
                            "sources": ["02大二/大二上/材料化学"],
                            "include": [],
                            "exclude": [],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
