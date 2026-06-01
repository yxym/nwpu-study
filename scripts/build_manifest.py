from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from scripts.archive_policy import CATEGORY_EXCLUDE, classify_path, load_whitelist

MANIFEST_REL = Path("docs/review/repo-manifest.json")
INDEX_REL = Path("收录内容.md")


def relative_file_entries(repo_root: Path, semester: str, course: str) -> list[dict[str, object]]:
    root = repo_root.resolve()
    course_dir = _resolve_under_repo(root, Path(semester) / course)
    if not course_dir.exists():
        return []
    if not course_dir.is_dir():
        raise ValueError(f"course path is not a directory: {Path(semester) / course}")

    entries: list[dict[str, object]] = []
    for path in sorted(course_dir.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            entries.append({"path": rel, "size": path.stat().st_size, "suffix": path.suffix.lower()})
    return entries


def build_manifest(repo_root: Path, whitelist_path: Path) -> list[dict[str, object]]:
    root = repo_root.resolve()
    whitelist = _resolve_whitelist(root, whitelist_path)
    config = load_whitelist(whitelist)

    manifest: list[dict[str, object]] = []
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
                "files": relative_file_entries(root, course.semester, course.target),
            }
        )
    return manifest


def write_manifest(repo_root: Path, manifest: list[dict[str, object]]) -> None:
    path = _resolve_under_repo(repo_root.resolve(), MANIFEST_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    for semester in sorted(grouped):
        lines.extend(
            [
                f"## {_escape_markdown_text(semester)}",
                "",
                "| 课程 | 文件数 | 文件类型 |",
                "| --- | ---: | --- |",
            ]
        )
        for course in sorted(grouped[semester], key=lambda item: str(item["course"])):
            files = list(course["files"])
            suffixes = sorted({str(file["suffix"]) or "无扩展名" for file in files})
            suffix_text = "、".join(suffixes) if suffixes else "暂无文件"
            lines.append(
                "| "
                f"{_escape_markdown_cell(str(course['course']))} | "
                f"{len(files)} | "
                f"{_escape_markdown_cell(suffix_text)} |"
            )
        lines.append("")

    path = _resolve_under_repo(repo_root.resolve(), INDEX_REL)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_checks(manifest: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for course in manifest:
        for file_entry in course["files"]:
            rel_path = Path(str(file_entry["path"]))
            classification = classify_path(rel_path)
            if classification.category == CATEGORY_EXCLUDE:
                errors.append(f"{rel_path.as_posix()}: {classification.reason}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成课程资料索引并检查公开边界。")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--whitelist", default="public-whitelist.yml")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    whitelist_path = _resolve_whitelist(repo_root, Path(args.whitelist))
    if not whitelist_path.exists():
        print(f"whitelist not found: {whitelist_path}", file=sys.stderr)
        return 2

    try:
        manifest = build_manifest(repo_root, whitelist_path)
        write_manifest(repo_root, manifest)
        write_index(repo_root, manifest)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"课程数：{len(manifest)}")

    if args.check:
        errors = run_checks(manifest)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if errors:
            return 2

    return 0


def _resolve_whitelist(repo_root: Path, whitelist_path: Path) -> Path:
    if whitelist_path.is_absolute():
        return whitelist_path
    return repo_root / whitelist_path


def _resolve_under_repo(repo_root: Path, rel_path: Path) -> Path:
    target = (repo_root / rel_path).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"path escapes repo root: {rel_path.as_posix()}") from exc
    return target


def _escape_markdown_cell(text: str) -> str:
    return _escape_markdown_text(text)


def _escape_markdown_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\r", "<br>")
        .replace("\n", "<br>")
    )


if __name__ == "__main__":
    raise SystemExit(main())
