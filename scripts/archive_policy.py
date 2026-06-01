from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

CATEGORY_INCLUDE = "建议收录"
CATEGORY_EXCLUDE = "建议排除"
CATEGORY_REVIEW = "需要人工判断"

JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_NAMES_LOWER = {name.lower() for name in JUNK_NAMES}
JUNK_PREFIXES = ("~$", "._", ".~")

PRIVATE_KEYWORDS = ["个人", "学生会", "名单", "报名表", "简历", "入党", "出国", "请假", "班级", "花名册"]
SENIOR_OR_OLD_KEYWORDS = ["学姐", "学长", "往年", "历年", "2022级之前", "资料出售", "出售"]
COURSEWARE_KEYWORDS = ["lecture", "课件", "slides", "chapter", "week", "module guide", "module_guide", "教学"]
INCLUDE_KEYWORDS = ["report", "报告", "作业", "homework", "coursework", "data", "原始数据", "raw data", "poster", "presentation", "答辩", "logbook", "worksheet", "工作簿", "代码", "复习", "总结", "笔记"]
TEXTBOOK_OR_ANSWER_KEYWORDS = ["教材", "课本", "ebook", "e-book", "textbook", "book", "答案", "answer", "answers", "solution", "solutions", "习题答案"]
AMBIGUOUS_KEYWORDS = ["chapter", "week", "module guide", "module_guide", "revision", "review", "zh-hans", "翻译"]
EXPLICIT_COURSEWARE_KEYWORDS = ["lecture", "课件", "slides"]


@dataclass(frozen=True)
class CourseEntry:
    semester: str
    target: str
    sources: list[str]
    include: list[str]
    exclude: list[str]
    prune: list[str]


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
        approved = data.get("approved", False)
        if not isinstance(approved, bool):
            raise ValueError("approved must be a bool")

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
            approved=approved,
        )


def load_whitelist(path: Path) -> WhitelistConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    courses = [
        CourseEntry(
            semester=str(course["semester"]),
            target=str(course["target"]),
            sources=[str(source) for source in course.get("sources", [])],
            include=[str(pattern) for pattern in course.get("include", [])],
            exclude=[str(pattern) for pattern in course.get("exclude", [])],
            prune=[str(pattern) for pattern in course.get("prune", [])],
        )
        for course in data.get("courses", [])
    ]
    return WhitelistConfig(source_root=Path(str(data["source_root"])), courses=courses)


def classify_path(path: Path, include: Iterable[str] = (), exclude: Iterable[str] = ()) -> Classification:
    path_text = path.as_posix()
    path_lower = path_text.lower()
    name = path.name
    name_lower = name.lower()

    if name_lower in JUNK_NAMES_LOWER or any(
        name_lower.startswith(prefix.lower()) for prefix in JUNK_PREFIXES
    ):
        return Classification(CATEGORY_EXCLUDE, "系统或临时文件")

    matched = _first_pattern(path, exclude)
    if matched is not None:
        return Classification(CATEGORY_EXCLUDE, f"命中课程排除规则：{matched}")

    matched = _first_keyword(path_lower, PRIVATE_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_EXCLUDE, f"命中隐私关键词：{matched}")

    matched = _first_keyword(path_lower, SENIOR_OR_OLD_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_EXCLUDE, f"命中历史或外部资料关键词：{matched}")

    matched = _first_pattern(path, include)
    if matched is not None:
        return Classification(CATEGORY_INCLUDE, f"命中课程收录规则：{matched}")

    matched = _first_keyword(name_lower, TEXTBOOK_OR_ANSWER_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_INCLUDE, f"命中教材或答案关键词：{matched}")

    matched = _first_keyword(path_lower, EXPLICIT_COURSEWARE_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_EXCLUDE, f"命中明确课件关键词：{matched}")

    matched = _first_keyword(name_lower, INCLUDE_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_INCLUDE, f"命中文件名：{matched}")

    matched = _first_keyword(name_lower, AMBIGUOUS_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_REVIEW, f"命中需人工判断关键词：{matched}")

    matched = _first_keyword(name_lower, COURSEWARE_KEYWORDS)
    if matched is not None:
        return Classification(CATEGORY_REVIEW, f"可能是课件或讲义：{matched}")

    return Classification(CATEGORY_REVIEW, "未命中明确规则")


def safe_target_path(repo_root: Path, target_rel: str | Path) -> Path:
    root = repo_root.resolve()
    target = (root / Path(target_rel)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"target path escapes archive root: {target_rel}") from exc
    return target


def unique_target_rel(target_rel: Path, used: set[str]) -> str:
    candidate = target_rel.as_posix()
    if candidate not in used:
        used.add(candidate)
        return candidate

    parent = target_rel.parent
    stem = target_rel.stem
    suffix = target_rel.suffix
    index = 2
    while True:
        candidate_path = parent / f"{stem}__{index}{suffix}"
        candidate = candidate_path.as_posix()
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def iter_source_files(root: Path, prune: Iterable[str] = ()) -> Iterable[Path]:
    prune_patterns = tuple(prune)
    if root.is_file():
        if not _matches_prune_path(Path(root.name), prune_patterns):
            yield root
        return
    if root.is_dir():
        for current, dirnames, filenames in os.walk(root):
            current_path = Path(current)
            dirnames.sort()
            filenames.sort()
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not _matches_prune_path((current_path / dirname).relative_to(root), prune_patterns)
            ]
            for filename in filenames:
                path = current_path / filename
                if not _matches_prune_path(path.relative_to(root), prune_patterns):
                    yield path


def make_candidate(
    source_root: Path,
    source_dir: Path,
    source_file: Path,
    course: CourseEntry,
    used_targets: set[str],
) -> Candidate:
    source_rel = source_file.relative_to(source_root)
    nested_rel = source_file.relative_to(source_dir) if source_dir.is_dir() else Path(source_file.name)
    classification = classify_path(source_rel, include=course.include, exclude=course.exclude)
    target_rel = unique_target_rel(Path(course.semester) / course.target / nested_rel, used_targets)

    return Candidate(
        source=source_file.as_posix(),
        source_rel=source_rel.as_posix(),
        target_rel=target_rel,
        semester=course.semester,
        course=course.target,
        size=source_file.stat().st_size,
        suffix=source_file.suffix.lower(),
        category=classification.category,
        reason=classification.reason,
    )


def collect_candidates(config: WhitelistConfig) -> list[Candidate]:
    candidates: list[Candidate] = []
    used_targets: set[str] = set()

    for course in config.courses:
        for source in course.sources:
            source_dir = config.source_root / source
            for source_file in iter_source_files(source_dir, prune=course.prune):
                candidates.append(make_candidate(config.source_root, source_dir, source_file, course, used_targets))

    return candidates


def _first_keyword(text: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword.lower() in text:
            return keyword
    return None


def _first_pattern(path: Path, patterns: Iterable[str]) -> str | None:
    path_text = path.as_posix().lower()
    name = path.name.lower()
    for pattern in patterns:
        pattern_text = pattern.lower()
        if fnmatch.fnmatch(path_text, pattern_text) or fnmatch.fnmatch(name, pattern_text):
            return pattern
    return None


def _matches_prune_path(path: Path, patterns: Iterable[str]) -> bool:
    path_text = path.as_posix().lower()
    for pattern in patterns:
        pattern_text = pattern.lower()
        if fnmatch.fnmatch(path_text, pattern_text):
            return True
        if pattern_text.endswith("/**"):
            subtree = pattern_text[:-3]
            if path_text == subtree or path_text.startswith(f"{subtree}/"):
                return True
    return False
