import json
import tempfile
import unittest
from pathlib import Path

from scripts.archive_policy import (
    CATEGORY_EXCLUDE,
    CATEGORY_INCLUDE,
    CATEGORY_REVIEW,
    Candidate,
    classify_path,
    load_whitelist,
    safe_target_path,
    unique_target_rel,
)


class ArchivePolicyTest(unittest.TestCase):
    def test_load_whitelist_json_compatible_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "public-whitelist.yml"
            path.write_text(
                json.dumps(
                    {
                        "source_root": "/tmp/source",
                        "courses": [
                            {
                                "semester": "大二上",
                                "target": "材料化学",
                                "sources": ["02大二/大二上/材料化学"],
                                "include": ["*report*"],
                                "exclude": ["*Lecture*"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            config = load_whitelist(path)

            self.assertEqual(config.source_root, Path("/tmp/source"))
            self.assertEqual(config.courses[0].semester, "大二上")
            self.assertEqual(config.courses[0].target, "材料化学")
            self.assertEqual(config.courses[0].sources, ["02大二/大二上/材料化学"])

    def test_classification_rules(self):
        self.assertEqual(classify_path(Path(".DS_Store")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("学姐资料/复习.docx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("Lecture 1.pptx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("QXU4007 EXP1-2 Report M9.docx")).category, CATEGORY_INCLUDE)
        self.assertEqual(classify_path(Path("托马斯微积分习题答案.pdf")).category, CATEGORY_INCLUDE)
        self.assertEqual(classify_path(Path("Chapter 1 Introduction.pdf")).category, CATEGORY_REVIEW)

    def test_safe_target_path_rejects_traversal(self):
        repo_root = Path("/tmp/repo")
        with self.assertRaises(ValueError):
            safe_target_path(repo_root, "../private.docx")

        target = safe_target_path(repo_root, "大二上/材料化学/report.docx")
        self.assertEqual(target, (repo_root / "大二上" / "材料化学" / "report.docx").resolve())

    def test_unique_target_rel_adds_deterministic_suffix(self):
        used = {"大二上/材料化学/report.docx"}

        target = unique_target_rel(Path("大二上/材料化学/report.docx"), used)

        self.assertEqual(target, "大二上/材料化学/report__2.docx")

    def test_candidate_round_trip(self):
        candidate = Candidate(
            source="/tmp/source/report.docx",
            source_rel="02大二/大二上/材料化学/report.docx",
            target_rel="大二上/材料化学/report.docx",
            semester="大二上",
            course="材料化学",
            size=12,
            suffix=".docx",
            category=CATEGORY_INCLUDE,
            reason="命中文件名：report",
            approved=False,
        )

        data = candidate.to_dict()
        restored = Candidate.from_dict(data)

        self.assertEqual(restored.target_rel, "大二上/材料化学/report.docx")
        self.assertFalse(restored.approved)


if __name__ == "__main__":
    unittest.main()
