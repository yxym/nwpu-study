# 西工大 QM 课程资料归档 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一个白名单驱动的西工大 QM 课程资料公开归档流程，先生成候选清单供人工复核，再按批准清单导入文件并生成仓库索引。

**Architecture:** 用 Python 标准库实现三个命令行脚本和一个共享规则模块：`archive_policy.py` 负责白名单、分类和路径安全；`collect_candidates.py` 只生成候选清单；`sync_public_files.py` 只复制人工批准的文件；`build_manifest.py` 生成索引并执行仓库校验。所有脚本只读取 `public-whitelist.yml` 中的来源目录，候选清单是实际导入前的人工闸门。

**Tech Stack:** Python 3 标准库、`unittest`、JSON-compatible YAML、Git LFS、Markdown。

---

## 文件结构与责任

- Create: `scripts/archive_policy.py`  
  共享规则模块。读取 JSON-compatible YAML 白名单，生成候选记录，分类文件，检查目标路径是否安全。
- Create: `scripts/collect_candidates.py`  
  CLI。扫描白名单来源，输出 `docs/review/candidates.md` 和 `docs/review/candidates.json`。
- Create: `scripts/sync_public_files.py`  
  CLI。读取人工编辑后的候选 JSON，只复制 `approved: true` 的文件。
- Create: `scripts/build_manifest.py`  
  CLI。扫描仓库内白名单课程目录，生成 `收录内容.md`、`docs/review/repo-manifest.json`，并做边界校验。
- Create: `public-whitelist.yml`  
  JSON-compatible YAML。列出允许扫描的学期、课程和来源目录。
- Create: `docs/public-file-policy.md`  
  中文公开边界说明。
- Create/Modify: `README.md`  
  中文项目首页。
- Create: `贡献方法.md`  
  中文贡献指南和隐私规则。
- Create: `收录内容.md`  
  由脚本生成的课程索引。
- Create: `tests/test_archive_policy.py`
- Create: `tests/test_collect_candidates.py`
- Create: `tests/test_sync_public_files.py`
- Create: `tests/test_build_manifest.py`

执行实现前，先按 `superpowers:using-git-worktrees` 检查是否需要隔离工作区。当前仓库已有用户课程资料改动，执行者不能回滚这些改动。

---

### Task 1: 共享规则模块与分类测试

**Files:**
- Create: `tests/test_archive_policy.py`
- Create: `scripts/archive_policy.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_archive_policy.py`:

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_archive_policy -v
```

Expected: FAIL，报错包含 `No module named 'scripts.archive_policy'` 或缺少对应函数。

- [ ] **Step 3: 实现共享规则模块**

Create `scripts/archive_policy.py`:

```python
from __future__ import annotations

import fnmatch
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

CATEGORY_INCLUDE = "建议收录"
CATEGORY_EXCLUDE = "建议排除"
CATEGORY_REVIEW = "需要人工判断"

JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_PREFIXES = ("~$", "._", ".~")

PRIVATE_KEYWORDS = [
    "个人",
    "学生会",
    "名单",
    "报名表",
    "简历",
    "入党",
    "出国",
    "请假",
    "班级",
    "花名册",
]

SENIOR_OR_OLD_KEYWORDS = [
    "学姐",
    "学长",
    "往年",
    "历年",
    "2022级之前",
    "资料出售",
    "出售",
]

COURSEWARE_KEYWORDS = [
    "lecture",
    "课件",
    "slides",
    "chapter",
    "week",
    "module guide",
    "module_guide",
    "教学",
]

INCLUDE_KEYWORDS = [
    "report",
    "报告",
    "作业",
    "homework",
    "coursework",
    "data",
    "原始数据",
    "raw data",
    "poster",
    "presentation",
    "答辩",
    "logbook",
    "worksheet",
    "工作簿",
    "代码",
    "复习",
    "总结",
    "笔记",
]

TEXTBOOK_OR_ANSWER_KEYWORDS = [
    "教材",
    "课本",
    "ebook",
    "e-book",
    "textbook",
    "book",
    "答案",
    "answer",
    "answers",
    "solution",
    "solutions",
    "习题答案",
]

AMBIGUOUS_KEYWORDS = [
    "chapter",
    "week",
    "module guide",
    "module_guide",
    "revision",
    "review",
    "zh-hans",
    "翻译",
]


@dataclass(frozen=True)
class CourseEntry:
    semester: str
    target: str
    sources: list[str]
    include: list[str]
    exclude: list[str]


@dataclass(frozen=True)
class WhitelistConfig:
    source_root: Path
    courses: list[CourseEntry]


@dataclass(frozen=True)
class Classification:
    category: str
    reason: str


@dataclass(frozen=True)
class Candidate:
    source: str
    source_rel: str
    target_rel: str
    semester: str
    course: str
    size: int
    suffix: str
    category: str
    reason: str
    approved: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Candidate":
        return cls(
            source=str(data["source"]),
            source_rel=str(data["source_rel"]),
            target_rel=str(data["target_rel"]),
            semester=str(data["semester"]),
            course=str(data["course"]),
            size=int(data["size"]),
            suffix=str(data["suffix"]),
            category=str(data["category"]),
            reason=str(data["reason"]),
            approved=bool(data.get("approved", False)),
        )


def load_whitelist(path: Path) -> WhitelistConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    courses = []
    for item in data["courses"]:
        courses.append(
            CourseEntry(
                semester=str(item["semester"]),
                target=str(item["target"]),
                sources=[str(source) for source in item["sources"]],
                include=[str(pattern) for pattern in item.get("include", [])],
                exclude=[str(pattern) for pattern in item.get("exclude", [])],
            )
        )
    return WhitelistConfig(source_root=Path(str(data["source_root"])), courses=courses)


def classify_path(path: Path, include: Iterable[str] = (), exclude: Iterable[str] = ()) -> Classification:
    normalized = str(path).replace("\\", "/")
    lowered = normalized.lower()
    name = path.name
    lowered_name = name.lower()

    if name in JUNK_NAMES or lowered_name.startswith(JUNK_PREFIXES):
        return Classification(CATEGORY_EXCLUDE, "本地系统或临时文件")

    for pattern in exclude:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern):
            return Classification(CATEGORY_EXCLUDE, f"命中课程排除规则：{pattern}")

    for keyword in PRIVATE_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_EXCLUDE, f"命中隐私/非课程关键词：{keyword}")

    for keyword in SENIOR_OR_OLD_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_EXCLUDE, f"命中学长学姐或往年资料关键词：{keyword}")

    for pattern in include:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern):
            return Classification(CATEGORY_INCLUDE, f"命中课程收录规则：{pattern}")

    for keyword in TEXTBOOK_OR_ANSWER_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_INCLUDE, f"命中教材/答案关键词：{keyword}")

    if "lecture" in lowered or "课件" in lowered or "slides" in lowered:
        return Classification(CATEGORY_EXCLUDE, "命中明确课件关键词")

    for keyword in INCLUDE_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_INCLUDE, f"命中课程产出关键词：{keyword}")

    for keyword in AMBIGUOUS_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_REVIEW, f"命中模糊关键词：{keyword}")

    for keyword in COURSEWARE_KEYWORDS:
        if keyword.lower() in lowered:
            return Classification(CATEGORY_REVIEW, f"可能是课件或讲义：{keyword}")

    return Classification(CATEGORY_REVIEW, "文件名不足以判断")


def safe_target_path(repo_root: Path, target_rel: str) -> Path:
    repo = repo_root.resolve()
    target = (repo / target_rel).resolve()
    if target != repo and repo not in target.parents:
        raise ValueError(f"目标路径越界：{target_rel}")
    return target


def unique_target_rel(target_rel: Path, used: set[str]) -> str:
    candidate = target_rel
    counter = 2
    while str(candidate) in used:
        candidate = target_rel.with_name(f"{target_rel.stem}__{counter}{target_rel.suffix}")
        counter += 1
    used.add(str(candidate))
    return str(candidate)


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path
```

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
python3 -m unittest tests.test_archive_policy -v
```

Expected: PASS，5 个测试通过。

- [ ] **Step 5: 提交**

Run:

```bash
git add scripts/archive_policy.py tests/test_archive_policy.py
git commit -m "Add archive policy rules"
```

Expected: commit 成功，只包含这两个文件。

---

### Task 2: 初始白名单配置

**Files:**
- Create: `public-whitelist.yml`
- Modify: `tests/test_archive_policy.py`

- [ ] **Step 1: 增加白名单结构测试**

Append to `tests/test_archive_policy.py` inside `ArchivePolicyTest`:

```python
    def test_project_whitelist_has_only_approved_semesters(self):
        config = load_whitelist(Path("public-whitelist.yml"))
        semesters = {course.semester for course in config.courses}

        self.assertEqual(semesters, {"大一上", "大一下", "大二上", "大二下", "大三上"})
        self.assertTrue(all(course.sources for course in config.courses))
        self.assertTrue(all(not source.startswith("../") for course in config.courses for source in course.sources))
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_archive_policy.ArchivePolicyTest.test_project_whitelist_has_only_approved_semesters -v
```

Expected: FAIL，报错包含 `No such file or directory: 'public-whitelist.yml'`。

- [ ] **Step 3: 创建 JSON-compatible YAML 白名单**

Create `public-whitelist.yml`:

```json
{
  "source_root": "/Users/chexuanming/Desktop/大学",
  "courses": [
    {
      "semester": "大一上",
      "target": "英语课",
      "sources": ["01大一/大一上/09英语课"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一上",
      "target": "faith",
      "sources": ["01大一/大一上/05faith课"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一上",
      "target": "公共教材与答案",
      "sources": ["01大一/大一上/11课本"],
      "include": ["*教材*", "*课本*", "*答案*", "*Calculus*", "*Physics*", "*线性代数*"],
      "exclude": []
    },
    {
      "semester": "大一下",
      "target": "科英",
      "sources": ["01大一/大一下/科英"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一下",
      "target": "高等数学",
      "sources": ["01大一/大一下/高等数学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一下",
      "target": "工程材料",
      "sources": ["01大一/大一下/工程材料"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一下",
      "target": "工程化学",
      "sources": ["01大一/大一下/工程化学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*", "*.pptx"]
    },
    {
      "semester": "大一下",
      "target": "计算方法",
      "sources": ["01大一/大一下/计算方法"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大一下",
      "target": "faith",
      "sources": ["01大一/大一下/faith"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "西方哲学史",
      "sources": ["02大二/大二上/西方哲学史"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二上",
      "target": "无机化学",
      "sources": ["02大二/大二上/无机化学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "习概",
      "sources": ["02大二/大二上/习概"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二上",
      "target": "材料化学",
      "sources": ["02大二/大二上/材料化学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "工程设计方法",
      "sources": ["02大二/大二上/工程设计方法"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "MS1 结构与性能",
      "sources": ["02大二/大二上/MS1 结构与性能"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "材料学实验1",
      "sources": ["02大二/大二上/材料学实验1"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二上",
      "target": "近代史纲要",
      "sources": ["02大二/大二上/近代史纲要"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二下",
      "target": "材料学2-加工与应用",
      "sources": ["02大二/大二下/材料学2-加工与应用"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "热力学与相变",
      "sources": ["02大二/大二下/热力学与相变"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "工程力学",
      "sources": ["02大二/大二下/工程力学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "材料学实验2",
      "sources": ["02大二/大二下/材料学实验2"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "中共党史",
      "sources": ["02大二/大二下/中共党史"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二下",
      "target": "MS2",
      "sources": ["02大二/大二下/MS2"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "大学美育",
      "sources": ["02大二/大二下/大学美育"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二下",
      "target": "毛概",
      "sources": ["02大二/大二下/毛概"],
      "include": [],
      "exclude": []
    },
    {
      "semester": "大二下",
      "target": "物理化学",
      "sources": ["02大二/大二下/物理化学"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大二下",
      "target": "faith",
      "sources": ["02大二/大二下/faith"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "马原",
      "sources": ["03大三上/马原"],
      "include": [],
      "exclude": ["*资料出售*"]
    },
    {
      "semester": "大三上",
      "target": "表面与界面",
      "sources": ["03大三上/2025表面与界面", "03大三上/表界面"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "结构表征",
      "sources": ["03大三上/2025结构表征", "03大三上/结构表征"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "科学与艺术",
      "sources": ["03大三上/科学与艺术"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "金属",
      "sources": ["03大三上/2025金属", "03大三上/金属"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "高分子物理",
      "sources": ["03大三上/2025高分子物理", "03大三上/高物"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    },
    {
      "semester": "大三上",
      "target": "faith_video",
      "sources": ["03大三上/faith_video"],
      "include": [],
      "exclude": ["*Lecture*", "*lecture*", "*课件*"]
    }
  ]
}
```

- [ ] **Step 4: 跑白名单测试**

Run:

```bash
python3 -m unittest tests.test_archive_policy -v
```

Expected: PASS，6 个测试通过。

- [ ] **Step 5: 提交**

Run:

```bash
git add public-whitelist.yml tests/test_archive_policy.py
git commit -m "Add public course whitelist"
```

Expected: commit 成功，只包含白名单和测试更新。

---

### Task 3: 候选清单生成脚本

**Files:**
- Create: `tests/test_collect_candidates.py`
- Create: `scripts/collect_candidates.py`
- Modify: `scripts/archive_policy.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_collect_candidates.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.collect_candidates import main


class CollectCandidatesTest(unittest.TestCase):
    def test_collects_only_whitelisted_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "大学"
            repo = root / "repo"
            course = source_root / "02大二" / "大二上" / "材料化学"
            private = source_root / "02大二" / "大二上" / "班级名单"
            course.mkdir(parents=True)
            private.mkdir(parents=True)
            (course / "M9 report.docx").write_text("report", encoding="utf-8")
            (course / "Lecture 1.pptx").write_text("slides", encoding="utf-8")
            (private / "名单.xlsx").write_text("private", encoding="utf-8")
            repo.mkdir()
            whitelist = repo / "public-whitelist.yml"
            whitelist.write_text(
                json.dumps(
                    {
                        "source_root": str(source_root),
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
            output_md = repo / "docs" / "review" / "candidates.md"
            output_json = repo / "docs" / "review" / "candidates.json"

            code = main(
                [
                    "--whitelist",
                    str(whitelist),
                    "--repo-root",
                    str(repo),
                    "--output-md",
                    str(output_md),
                    "--output-json",
                    str(output_json),
                ]
            )

            self.assertEqual(code, 0)
            md = output_md.read_text(encoding="utf-8")
            data = json.loads(output_json.read_text(encoding="utf-8"))
            paths = "\n".join(item["source_rel"] for item in data)

            self.assertIn("M9 report.docx", md)
            self.assertIn("Lecture 1.pptx", md)
            self.assertNotIn("班级名单", paths)
            self.assertEqual(len(data), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_collect_candidates -v
```

Expected: FAIL，报错包含 `No module named 'scripts.collect_candidates'`。

- [ ] **Step 3: 扩展共享模块**

Append to `scripts/archive_policy.py`:

```python

def make_candidate(
    source_root: Path,
    source_dir: Path,
    source_file: Path,
    course: CourseEntry,
    used_targets: set[str],
) -> Candidate:
    source_rel = source_file.relative_to(source_root)
    nested_rel = source_file.relative_to(source_dir)
    target_rel = unique_target_rel(Path(course.semester) / course.target / nested_rel, used_targets)
    classification = classify_path(source_rel, include=course.include, exclude=course.exclude)
    return Candidate(
        source=str(source_file),
        source_rel=str(source_rel),
        target_rel=target_rel,
        semester=course.semester,
        course=course.target,
        size=source_file.stat().st_size,
        suffix=source_file.suffix.lower(),
        category=classification.category,
        reason=classification.reason,
        approved=False,
    )


def collect_candidates(config: WhitelistConfig) -> list[Candidate]:
    candidates: list[Candidate] = []
    used_targets: set[str] = set()
    for course in config.courses:
        for source in course.sources:
            source_dir = config.source_root / source
            if not source_dir.exists():
                continue
            for source_file in iter_source_files(source_dir):
                candidates.append(make_candidate(config.source_root, source_dir, source_file, course, used_targets))
    return candidates
```

- [ ] **Step 4: 实现候选清单 CLI**

Create `scripts/collect_candidates.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from scripts.archive_policy import Candidate, collect_candidates, load_whitelist


def write_json(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.to_dict() for candidate in candidates], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_markdown(path: Path, candidates: list[Candidate]) -> None:
    grouped: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate.semester, candidate.course)].append(candidate)

    lines = [
        "# 候选文件清单",
        "",
        "此文件由 `scripts/collect_candidates.py` 生成。实际导入前，请在 `docs/review/candidates.json` 中把确认公开的文件设为 `approved: true`。",
        "",
    ]

    for (semester, course), items in sorted(grouped.items()):
        lines.extend(
            [
                f"## {semester} / {course}",
                "",
                "| 分类 | 理由 | 大小 | 来源 | 目标 |",
                "|---|---|---:|---|---|",
            ]
        )
        for item in items:
            lines.append(
                f"| {item.category} | {item.reason} | {item.size} | `{item.source_rel}` | `{item.target_rel}` |"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成公开课程资料候选清单")
    parser.add_argument("--whitelist", default="public-whitelist.yml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-md", default="docs/review/candidates.md")
    parser.add_argument("--output-json", default="docs/review/candidates.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    config = load_whitelist(Path(args.whitelist))
    candidates = collect_candidates(config)
    write_markdown(repo_root / args.output_md, candidates)
    write_json(repo_root / args.output_json, candidates)
    print(f"候选文件：{len(candidates)}")
    print(f"Markdown: {repo_root / args.output_md}")
    print(f"JSON: {repo_root / args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 跑测试确认通过**

Run:

```bash
python3 -m unittest tests.test_archive_policy tests.test_collect_candidates -v
```

Expected: PASS，所有测试通过。

- [ ] **Step 6: 提交**

Run:

```bash
git add scripts/archive_policy.py scripts/collect_candidates.py tests/test_collect_candidates.py
git commit -m "Add candidate collection script"
```

Expected: commit 成功，只包含候选清单脚本、共享模块更新和测试。

---

### Task 4: 同步脚本，只复制人工批准文件

**Files:**
- Create: `tests/test_sync_public_files.py`
- Create: `scripts/sync_public_files.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_sync_public_files.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_public_files import main


class SyncPublicFilesTest(unittest.TestCase):
    def test_dry_run_does_not_copy_and_real_run_copies_only_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            repo = root / "repo"
            source.mkdir()
            repo.mkdir()
            approved = source / "approved.docx"
            rejected = source / "rejected.docx"
            approved.write_text("yes", encoding="utf-8")
            rejected.write_text("no", encoding="utf-8")
            review = repo / "docs" / "review" / "candidates.json"
            review.parent.mkdir(parents=True)
            review.write_text(
                json.dumps(
                    [
                        {
                            "source": str(approved),
                            "source_rel": "course/approved.docx",
                            "target_rel": "大二上/材料化学/approved.docx",
                            "semester": "大二上",
                            "course": "材料化学",
                            "size": 3,
                            "suffix": ".docx",
                            "category": "建议收录",
                            "reason": "test",
                            "approved": True,
                        },
                        {
                            "source": str(rejected),
                            "source_rel": "course/rejected.docx",
                            "target_rel": "大二上/材料化学/rejected.docx",
                            "semester": "大二上",
                            "course": "材料化学",
                            "size": 2,
                            "suffix": ".docx",
                            "category": "建议收录",
                            "reason": "test",
                            "approved": False,
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            dry_code = main(["--repo-root", str(repo), "--review-json", str(review), "--dry-run"])
            self.assertEqual(dry_code, 0)
            self.assertFalse((repo / "大二上" / "材料化学" / "approved.docx").exists())

            real_code = main(["--repo-root", str(repo), "--review-json", str(review)])
            self.assertEqual(real_code, 0)
            self.assertTrue((repo / "大二上" / "材料化学" / "approved.docx").exists())
            self.assertFalse((repo / "大二上" / "材料化学" / "rejected.docx").exists())
            self.assertTrue((repo / "docs" / "review" / "imported-manifest.json").exists())

    def test_rejects_target_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.docx"
            repo = root / "repo"
            source.write_text("x", encoding="utf-8")
            repo.mkdir()
            review = repo / "candidates.json"
            review.write_text(
                json.dumps(
                    [
                        {
                            "source": str(source),
                            "source_rel": "source.docx",
                            "target_rel": "../escape.docx",
                            "semester": "大二上",
                            "course": "材料化学",
                            "size": 1,
                            "suffix": ".docx",
                            "category": "建议收录",
                            "reason": "test",
                            "approved": True,
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            code = main(["--repo-root", str(repo), "--review-json", str(review)])

            self.assertEqual(code, 2)
            self.assertFalse((root / "escape.docx").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_sync_public_files -v
```

Expected: FAIL，报错包含 `No module named 'scripts.sync_public_files'`。

- [ ] **Step 3: 实现同步 CLI**

Create `scripts/sync_public_files.py`:

```python
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from scripts.archive_policy import Candidate, safe_target_path


def load_candidates(path: Path) -> list[Candidate]:
    return [Candidate.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def write_manifest(repo_root: Path, imported: list[Candidate]) -> None:
    path = repo_root / "docs" / "review" / "imported-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.to_dict() for candidate in imported], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="复制人工批准公开的课程资料")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--review-json", default="docs/review/candidates.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    review_path = Path(args.review_json)
    candidates = load_candidates(review_path)
    approved = [candidate for candidate in candidates if candidate.approved]
    imported: list[Candidate] = []

    try:
        for candidate in approved:
            source = Path(candidate.source)
            target = safe_target_path(repo_root, candidate.target_rel)
            if not source.exists():
                print(f"来源不存在，跳过：{source}")
                continue
            if args.dry_run:
                print(f"[dry-run] {source} -> {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            imported.append(candidate)
            print(f"copied: {source} -> {target}")
    except ValueError as error:
        print(str(error))
        return 2

    if not args.dry_run:
        write_manifest(repo_root, imported)
    print(f"批准文件：{len(approved)}")
    print(f"实际复制：{len(imported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
python3 -m unittest tests.test_sync_public_files -v
```

Expected: PASS，2 个测试通过。

- [ ] **Step 5: 提交**

Run:

```bash
git add scripts/sync_public_files.py tests/test_sync_public_files.py
git commit -m "Add approved file sync script"
```

Expected: commit 成功，只包含同步脚本和测试。

---

### Task 5: 索引生成与仓库校验

**Files:**
- Create: `tests/test_build_manifest.py`
- Create: `scripts/build_manifest.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_build_manifest.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_manifest import main


class BuildManifestTest(unittest.TestCase):
    def test_builds_index_for_whitelisted_course_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "大二上" / "材料化学").mkdir(parents=True)
            (repo / "大二上" / "材料化学" / "report.docx").write_text("x", encoding="utf-8")
            whitelist = repo / "public-whitelist.yml"
            whitelist.write_text(
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

            code = main(["--repo-root", str(repo), "--whitelist", str(whitelist)])

            self.assertEqual(code, 0)
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
            whitelist.write_text(
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

            code = main(["--repo-root", str(repo), "--whitelist", str(whitelist), "--check"])

            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
python3 -m unittest tests.test_build_manifest -v
```

Expected: FAIL，报错包含 `No module named 'scripts.build_manifest'`。

- [ ] **Step 3: 实现索引和校验 CLI**

Create `scripts/build_manifest.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from scripts.archive_policy import CATEGORY_EXCLUDE, classify_path, load_whitelist


def relative_file_entries(repo_root: Path, semester: str, course: str) -> list[dict[str, object]]:
    course_dir = repo_root / semester / course
    entries: list[dict[str, object]] = []
    if not course_dir.exists():
        return entries
    for path in sorted(course_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(repo_root)
            entries.append({"path": str(rel), "size": path.stat().st_size, "suffix": path.suffix.lower()})
    return entries


def build_manifest(repo_root: Path, whitelist_path: Path) -> list[dict[str, object]]:
    config = load_whitelist(whitelist_path)
    manifest = []
    seen: set[tuple[str, str]] = set()
    for course in config.courses:
        key = (course.semester, course.target)
        if key in seen:
            continue
        seen.add(key)
        manifest.append(
            {
                "semester": course.semester,
                "course": course.target,
                "files": relative_file_entries(repo_root, course.semester, course.target),
            }
        )
    return manifest


def write_manifest(repo_root: Path, manifest: list[dict[str, object]]) -> None:
    path = repo_root / "docs" / "review" / "repo-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_index(repo_root: Path, manifest: list[dict[str, object]]) -> None:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for course in manifest:
        grouped[str(course["semester"])].append(course)

    lines = [
        "# 收录内容",
        "",
        "本文件由 `scripts/build_manifest.py` 生成，按学期和课程列出当前仓库已收录资料。",
        "",
    ]
    for semester, courses in sorted(grouped.items()):
        lines.extend([f"## {semester}", "", "| 课程 | 文件数 | 主要类型 |", "|---|---:|---|"])
        for course in sorted(courses, key=lambda item: str(item["course"])):
            files = list(course["files"])
            suffixes = sorted({str(file["suffix"]) or "无扩展名" for file in files})
            suffix_text = "、".join(suffixes) if suffixes else "暂无文件"
            lines.append(f"| {course['course']} | {len(files)} | {suffix_text} |")
        lines.append("")

    (repo_root / "收录内容.md").write_text("\n".join(lines), encoding="utf-8")


def run_checks(manifest: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for course in manifest:
        for file in course["files"]:
            rel_path = Path(str(file["path"]))
            classification = classify_path(rel_path)
            if classification.category == CATEGORY_EXCLUDE:
                errors.append(f"{rel_path}: {classification.reason}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成课程资料索引并检查公开边界")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--whitelist", default="public-whitelist.yml")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    manifest = build_manifest(repo_root, Path(args.whitelist))
    write_manifest(repo_root, manifest)
    write_index(repo_root, manifest)

    if args.check:
        errors = run_checks(manifest)
        for error in errors:
            print(f"ERROR: {error}")
        if errors:
            return 2

    print(f"课程数：{len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run:

```bash
python3 -m unittest tests.test_build_manifest -v
```

Expected: PASS，2 个测试通过。

- [ ] **Step 5: 提交**

Run:

```bash
git add scripts/build_manifest.py tests/test_build_manifest.py
git commit -m "Add archive manifest builder"
```

Expected: commit 成功，只包含索引脚本和测试。

---

### Task 6: 项目文档中文化与公开边界说明

**Files:**
- Modify: `README.md`
- Create: `贡献方法.md`
- Create: `docs/public-file-policy.md`
- Modify/Create: `收录内容.md`

- [ ] **Step 1: 写 README 内容**

Replace `README.md` with:

```markdown
# 西工大 QM 课程资料整理

> 本仓库整理西北工业大学伦敦玛丽女王大学工程学院部分课程资料，包含作业、实验报告、原始数据、复习整理、教材/电子书和老师发的答案等。

灵感来源：[PKUanonym/REKCARC-TSC-UHT](https://github.com/PKUanonym/REKCARC-TSC-UHT)。

## 收录范围

第一版覆盖：

- 大一上
- 大一下
- 大二上
- 大二下
- 大三上

具体课程和资料类型见 [收录内容](收录内容.md)。

## 公开边界

本仓库使用白名单制整理资料。只有明确列入 `public-whitelist.yml` 的学期和课程会进入候选清单，其它本地文件默认不公开。

本仓库不收录：

- 课件和 lecture slides
- 学长学姐资料
- 往年资料
- 学生会、班级名单、报名表、简历、入党、出国等非课程或隐私资料

详细规则见 [公开文件规则](docs/public-file-policy.md)。

## 使用说明

克隆仓库：

```bash
git clone https://github.com/yxym/nwpu-study.git
```

本仓库使用 Git LFS 管理部分大文件。首次使用前请安装并启用 Git LFS：

```bash
git lfs install
```

## 学术诚信

资料仅供学习参考。请遵守学校课程要求、考试纪律和学术诚信规范，不要直接抄袭作业、报告或课程项目。

## 贡献

欢迎通过 Pull Request 补充资料、修正索引或改进整理规则。提交前请阅读 [贡献方法](贡献方法.md)。

## 许可与版权

贡献者原创整理部分建议采用 CC BY-NC-SA 4.0 方式共享。教材、电子书、老师发放资料及其它非原创材料版权归原作者或权利方所有，仅作学习参考。
```

- [ ] **Step 2: 写贡献指南**

Create `贡献方法.md`:

```markdown
# 贡献方法

欢迎补充课程资料、修正文件分类、改进 README 或完善脚本。

## 提交流程

1. Fork 本仓库。
2. 创建分支，例如 `add/材料化学-notes`。
3. 只添加确认可以公开的课程资料。
4. 运行索引和校验命令。
5. 提交 Pull Request，并说明资料来源和所属课程。

## 可以贡献的内容

- 个人课程作业
- 实验报告
- 原始数据
- 个人复习笔记和总结
- 课程项目产出
- 教材、电子书、老师发的答案

## 不要贡献的内容

- 课件和 lecture slides
- 学长学姐资料
- 往年资料
- 学生会、班级名单、报名表、简历、入党、出国等非课程或隐私资料
- 未确认可以公开的他人文件

## 命名建议

文件名尽量保留原名。新增整理资料建议包含课程名、资料类型和年份，例如：

```text
材料化学-复习总结-2024.pdf
QXU4007-EXP1-2-Report-M9.docx
```

## 生成索引

更新资料后运行：

```bash
python3 scripts/build_manifest.py --check
```

如果校验报错，请先处理被标出的文件路径。
```

- [ ] **Step 3: 写公开规则文档**

Create `docs/public-file-policy.md`:

```markdown
# 公开文件规则

本仓库采用白名单制。只有 `public-whitelist.yml` 中列出的学期和课程目录会被扫描，其它本地目录默认不公开。

## 可以收录

- 个人课程作业
- 实验报告
- 原始数据
- 含本人姓名、学号或小组信息的课程文件
- 教材和电子书
- 老师发的答案
- 自己整理的笔记、总结、复习资料、代码、poster、presentation 和课程产出

## 不收录

- 课件和 lecture slides
- 学长学姐资料
- 往年资料
- 学生会材料
- 班级名单、花名册、报名表
- 简历、入党、出国、请假等个人事务材料
- 不能确认公开授权的他人文件

## 候选清单

运行：

```bash
python3 scripts/collect_candidates.py
```

脚本会生成：

- `docs/review/candidates.md`
- `docs/review/candidates.json`

实际导入前，需要人工检查候选清单，并在 JSON 中把确认公开的文件设为：

```json
"approved": true
```

未显式批准的文件不会被同步脚本复制。

## 导入命令

预览复制：

```bash
python3 scripts/sync_public_files.py --dry-run
```

执行复制：

```bash
python3 scripts/sync_public_files.py
```

复制后运行：

```bash
python3 scripts/build_manifest.py --check
```
```

- [ ] **Step 4: 生成初始收录内容**

Run:

```bash
python3 scripts/build_manifest.py
```

Expected: 生成或更新 `收录内容.md` 和 `docs/review/repo-manifest.json`。

- [ ] **Step 5: 提交**

Run:

```bash
git add README.md 贡献方法.md docs/public-file-policy.md 收录内容.md docs/review/repo-manifest.json
git commit -m "Document public archive policy"
```

Expected: commit 成功，包含中文文档和初始索引。

---

### Task 7: 端到端候选清单生成，不导入文件

**Files:**
- Create/Modify: `docs/review/candidates.md`
- Create/Modify: `docs/review/candidates.json`

- [ ] **Step 1: 跑全部单元测试**

Run:

```bash
python3 -m unittest discover -v
```

Expected: PASS，所有测试通过。

- [ ] **Step 2: 生成候选清单**

Run:

```bash
python3 scripts/collect_candidates.py
```

Expected: 输出候选文件数量，并写入：

```text
docs/review/candidates.md
docs/review/candidates.json
```

- [ ] **Step 3: 检查候选清单里是否暴露明显非课程目录**

Run:

```bash
rg -n "学生会|报名表|简历|入党|出国|班级名单|花名册|学姐|学长|往年|资料出售" docs/review/candidates.md docs/review/candidates.json
```

Expected: 无输出。如果有输出，不提交候选清单，不继续导入；先把命中行发给用户确认，再决定是收紧 `public-whitelist.yml`、改分类规则，还是允许这些候选路径只作为本地 review 文件保留。

- [ ] **Step 4: 在未暴露明显非课程目录时提交候选清单供人工 review**

Run:

```bash
git add docs/review/candidates.md docs/review/candidates.json
git commit -m "Generate public course candidate list"
```

Expected: commit 成功，只包含候选清单。

- [ ] **Step 5: 停止并让用户 review**

Send this message to the user:

```text
候选清单已生成：docs/review/candidates.md 和 docs/review/candidates.json。请先 review，把确认公开的文件在 JSON 中设为 "approved": true。确认后我再执行 dry-run 和实际导入。
```

Expected: 不运行 `scripts/sync_public_files.py` 的实际复制命令，直到用户明确批准候选清单。

---

### Task 8: 人工批准后同步文件并校验

**Files:**
- Modify: approved course directories under `大一上/`, `大一下/`, `大二上/`, `大二下/`, `大三上/`
- Modify: `docs/review/imported-manifest.json`
- Modify: `docs/review/repo-manifest.json`
- Modify: `收录内容.md`

- [ ] **Step 1: 确认候选 JSON 存在批准项**

Run:

```bash
python3 -c "import json; data=json.load(open('docs/review/candidates.json', encoding='utf-8')); print(sum(1 for item in data if item.get('approved') is True))"
```

Expected: 输出大于 0 的整数。若输出 `0`，停止并请用户先批准候选文件。

- [ ] **Step 2: dry-run 预览复制**

Run:

```bash
python3 scripts/sync_public_files.py --dry-run
```

Expected: 只打印 `approved: true` 文件的复制路径，不创建新课程文件。

- [ ] **Step 3: 执行复制**

Run:

```bash
python3 scripts/sync_public_files.py
```

Expected: 复制批准文件，并生成 `docs/review/imported-manifest.json`。

- [ ] **Step 4: 更新索引并校验**

Run:

```bash
python3 scripts/build_manifest.py --check
```

Expected: 退出码 0，更新 `收录内容.md` 和 `docs/review/repo-manifest.json`。

- [ ] **Step 5: 检查 Git LFS 跟踪**

Run:

```bash
git lfs track
```

Expected: 输出包含 `*.xlsx`、`*.zip`、`*.pptx`、`*.docx`。如果缺少某类扩展名，先更新 `.gitattributes` 并提交。

- [ ] **Step 6: 跑全部测试**

Run:

```bash
python3 -m unittest discover -v
```

Expected: PASS，所有测试通过。

- [ ] **Step 7: 状态检查**

Run:

```bash
git -c filter.lfs.process= -c filter.lfs.clean= -c filter.lfs.required=false status --short --branch
```

Expected: 只显示本次批准导入和生成索引相关的文件改动；不应出现白名单外目录。

- [ ] **Step 8: 提交导入结果**

Run:

```bash
git add 大一上 大一下 大二上 大二下 大三上 docs/review/imported-manifest.json docs/review/repo-manifest.json 收录内容.md
git commit -m "Import approved public course materials"
```

Expected: commit 成功，只包含批准导入的课程资料和生成索引。

---

## 最终验证

- [ ] Run:

```bash
python3 -m unittest discover -v
```

Expected: PASS。

- [ ] Run:

```bash
python3 scripts/build_manifest.py --check
```

Expected: 退出码 0。

- [ ] Run:

```bash
rg -n "学生会|报名表|简历|入党|出国|班级名单|花名册|学姐|学长|往年|资料出售" 大一上 大一下 大二上 大二下 大三上
```

Expected: 无输出。

- [ ] Run:

```bash
git -c filter.lfs.process= -c filter.lfs.clean= -c filter.lfs.required=false status --short --branch
```

Expected: 没有未解释的改动；若仓库已有用户改动，最终报告要明确区分本次改动和既有改动。

---

## 人工闸门

Task 7 结束后必须停下，让用户 review `docs/review/candidates.md` 和 `docs/review/candidates.json`。只有用户明确确认候选清单并设置 `approved: true` 后，才执行 Task 8 的实际复制。
