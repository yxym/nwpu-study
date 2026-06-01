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
    iter_source_files,
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
                                "prune": ["private/**"],
                            },
                            {
                                "semester": "大二上",
                                "target": "工程设计方法",
                                "sources": ["02大二/大二上/工程设计方法"],
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

            config = load_whitelist(path)

            self.assertEqual(config.source_root, Path("/tmp/source"))
            self.assertEqual(config.courses[0].semester, "大二上")
            self.assertEqual(config.courses[0].target, "材料化学")
            self.assertEqual(config.courses[0].sources, ["02大二/大二上/材料化学"])
            self.assertEqual(config.courses[0].prune, ["private/**"])
            self.assertEqual(config.courses[1].prune, [])

    def test_classification_rules(self):
        self.assertEqual(classify_path(Path(".DS_Store")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("thumbs.db")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("Desktop.ini")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("学姐资料/复习.docx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("Lecture 1.pptx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("课件/report.docx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("QXU4007 EXP1-2 Report M9.docx")).category, CATEGORY_INCLUDE)
        self.assertEqual(classify_path(Path("托马斯微积分习题答案.pdf")).category, CATEGORY_INCLUDE)
        self.assertEqual(classify_path(Path("Practice Questions with Solution.pdf")).category, CATEGORY_INCLUDE)
        self.assertEqual(classify_path(Path("Chapter 9 The Behavior of Solutions.pdf")).category, CATEGORY_REVIEW)
        self.assertEqual(classify_path(Path("2024_第15节_Analyses of XPS Data_(2学时).pptx")).category, CATEGORY_EXCLUDE)
        self.assertEqual(classify_path(Path("Chapter 1 Introduction.pdf")).category, CATEGORY_REVIEW)
        teaching_schedule = classify_path(Path("教学安排.pdf"))
        self.assertEqual(teaching_schedule.category, CATEGORY_REVIEW)
        self.assertIn("可能是课件或讲义：教学", teaching_schedule.reason)

    def test_course_patterns_have_expected_priority(self):
        self.assertEqual(
            classify_path(Path("Lecture report.pptx")).category,
            CATEGORY_EXCLUDE,
        )
        self.assertEqual(
            classify_path(Path("final-report.docx"), exclude=["*final-report*"]).category,
            CATEGORY_EXCLUDE,
        )
        self.assertEqual(
            classify_path(Path("custom artifact.bin"), include=["*artifact*"]).category,
            CATEGORY_INCLUDE,
        )

    def test_iter_source_files_recurses_single_root_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "b"
            nested.mkdir()
            (nested / "2.txt").write_text("2", encoding="utf-8")
            (root / "a.txt").write_text("1", encoding="utf-8")

            files = list(iter_source_files(root))

            self.assertEqual(files, [root / "a.txt", nested / "2.txt"])

    def test_iter_source_files_prunes_matching_subtrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / "case study个人"
            private.mkdir()
            (private / "hidden.txt").write_text("hidden", encoding="utf-8")
            (root / "visible.txt").write_text("visible", encoding="utf-8")

            files = list(iter_source_files(root, prune=["case study个人/**"]))

            self.assertEqual(files, [root / "visible.txt"])

    def test_iter_source_files_skips_junk_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "nested"
            nested.mkdir()
            (root / ".DS_Store").write_text("metadata", encoding="utf-8")
            (root / "~$temp.docx").write_text("lock", encoding="utf-8")
            (nested / "Thumbs.db").write_text("thumbs", encoding="utf-8")
            (nested / "desktop.ini").write_text("desktop", encoding="utf-8")
            (nested / "._report.docx").write_text("resource fork", encoding="utf-8")
            (nested / ".~report.docx").write_text("backup", encoding="utf-8")
            (nested / "report.docx").write_text("report", encoding="utf-8")

            files = list(iter_source_files(root))

            self.assertEqual(files, [nested / "report.docx"])

    def test_safe_target_path_rejects_traversal(self):
        repo_root = Path("/tmp/repo")
        with self.assertRaises(ValueError):
            safe_target_path(repo_root, "../private.docx")

        target = safe_target_path(repo_root, "大二上/材料化学/report.docx")
        self.assertEqual(target, (repo_root / "大二上" / "材料化学" / "report.docx").resolve())

    def test_safe_target_path_rejects_absolute_target_inside_repo(self):
        repo_root = Path("/tmp/repo")

        with self.assertRaisesRegex(ValueError, "target path must be relative"):
            safe_target_path(repo_root, repo_root / "public" / "x.docx")

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

    def test_candidate_rejects_non_bool_approved(self):
        data = {
            "source": "/tmp/source/report.docx",
            "source_rel": "02大二/大二上/材料化学/report.docx",
            "target_rel": "大二上/材料化学/report.docx",
            "semester": "大二上",
            "course": "材料化学",
            "size": 12,
            "suffix": ".docx",
            "category": CATEGORY_INCLUDE,
            "reason": "命中文件名：report",
            "approved": "false",
        }

        with self.assertRaises(ValueError):
            Candidate.from_dict(data)

    def test_project_whitelist_has_only_approved_semesters(self):
        config = load_whitelist(Path("public-whitelist.yml"))
        semesters = {course.semester for course in config.courses}

        self.assertEqual(semesters, {"大一上", "大一下", "大二上", "大二下", "大三上"})
        self.assertTrue(all(course.sources for course in config.courses))
        self.assertTrue(all(not source.startswith("../") for course in config.courses for source in course.sources))

    def test_project_whitelist_does_not_publish_private_paths(self):
        config = load_whitelist(Path("public-whitelist.yml"))
        dangerous_keywords = [
            "个人",
            "学生会",
            "班级",
            "名单",
            "报名表",
            "简历",
            "入党",
            "出国",
            "学姐",
            "学长",
            "往年",
            "资料出售",
        ]

        for course in config.courses:
            self.assertFalse(Path(course.target).is_absolute(), course.target)
            self.assertNotIn("..", Path(course.target).parts, course.target)
            self.assertFalse(any(keyword in course.target for keyword in dangerous_keywords), course.target)

            for source in course.sources:
                self.assertFalse(Path(source).is_absolute(), source)
                self.assertNotIn("..", Path(source).parts, source)
                self.assertFalse(any(keyword in source for keyword in dangerous_keywords), source)

        keying = next(course for course in config.courses if course.semester == "大一下" and course.target == "科英")
        self.assertIn("case study个人/**", keying.prune)

        mayuan = next(course for course in config.courses if course.semester == "大三上" and course.target == "马原")
        self.assertIn("马原资料出售/**", mayuan.prune)


if __name__ == "__main__":
    unittest.main()
