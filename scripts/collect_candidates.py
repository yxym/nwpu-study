from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from scripts.archive_policy import Candidate, collect_candidates, load_whitelist, validate_source_dirs


def write_json(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.to_dict() for candidate in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, candidates: list[Candidate], json_path: Path) -> None:
    grouped: dict[tuple[str, str], list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate.semester, candidate.course)].append(candidate)

    lines = [
        "# 候选清单",
        "",
        "此文件由 `scripts/collect_candidates.py` 生成。实际导入需要在 JSON 中将确认公开的条目设置为 `approved: true`。",
        "",
        f"- JSON: `{json_path.as_posix()}`",
        f"- 候选文件数: {len(candidates)}",
    ]

    for (semester, course), items in grouped.items():
        lines.extend(
            [
                "",
                f"## {_escape_markdown_text(semester)} / {_escape_markdown_text(course)}",
                "",
                "| 分类 | 源文件 | 目标路径 | 大小 | 理由 |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for candidate in items:
            lines.append(
                "| "
                f"{_escape_markdown_cell(candidate.category)} | "
                f"{_escape_markdown_cell(candidate.source_rel)} | "
                f"{_escape_markdown_cell(candidate.target_rel)} | "
                f"{candidate.size} | "
                f"{_escape_markdown_cell(candidate.reason)} |"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate public archive candidate review files.")
    parser.add_argument("--whitelist", default="public-whitelist.yml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-md", default="docs/review/candidates.md")
    parser.add_argument("--output-json", default="docs/review/candidates.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    whitelist_path = _resolve_under(repo_root, args.whitelist)
    try:
        output_md = _resolve_output_path(repo_root, args.output_md)
        output_json = _resolve_output_path(repo_root, args.output_json)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    config = load_whitelist(whitelist_path)
    missing_sources = validate_source_dirs(config)
    if missing_sources:
        print("Missing source paths:", file=sys.stderr)
        for path in missing_sources:
            print(f"- {path}", file=sys.stderr)
        return 2

    candidates = collect_candidates(config)
    write_json(output_json, candidates)
    write_markdown(output_md, candidates, output_json)

    print(f"Wrote {len(candidates)} candidates to {output_md} and {output_json}")
    return 0


def _resolve_under(root: Path, path: str) -> Path:
    value = Path(path)
    if value.is_absolute():
        return value
    return root / value


def _resolve_output_path(repo_root: Path, path: str) -> Path:
    value = Path(path)
    target = value.resolve() if value.is_absolute() else (repo_root / value).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"output path escapes repo root: {path}") from exc
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
