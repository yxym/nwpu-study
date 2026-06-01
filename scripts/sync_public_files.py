from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from scripts.archive_policy import Candidate, safe_target_path

MANIFEST_REL = Path("docs/review/imported-manifest.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy approved public archive candidates into the repo.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--review-json", default="docs/review/candidates.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()

    try:
        review_json = _resolve_review_json(repo_root, args.review_json)
        candidates = _load_candidates(review_json)
        approved = [candidate for candidate in candidates if candidate.approved is True]
        planned = _plan_copies(repo_root, approved)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.dry_run:
        for candidate, target in planned:
            print(f"{candidate.source} -> {target.as_posix()}")
        print(f"Planned {len(planned)} approved copies")
        return 0

    try:
        _copy_candidates(planned)
        manifest_path = safe_target_path(repo_root, MANIFEST_REL)
        _write_manifest(manifest_path, [candidate for candidate, _target in planned])
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"Imported {len(planned)} files to {manifest_path.as_posix()}")
    return 0


def _resolve_review_json(repo_root: Path, path: str) -> Path:
    value = Path(path)
    target = value.resolve() if value.is_absolute() else (repo_root / value).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"review JSON path escapes repo root: {path}") from exc
    return target


def _load_candidates(path: Path) -> list[Candidate]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("review JSON must contain a list of candidates")

    candidates: list[Candidate] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"candidate #{index + 1} must be an object")
        candidates.append(Candidate.from_dict(item))
    return candidates


def _plan_copies(repo_root: Path, candidates: list[Candidate]) -> list[tuple[Candidate, Path]]:
    planned: list[tuple[Candidate, Path]] = []
    for candidate in candidates:
        target = safe_target_path(repo_root, candidate.target_rel)
        source = Path(candidate.source)
        if not source.is_file():
            raise ValueError(f"source file does not exist: {candidate.source}")
        planned.append((candidate, target))
    return planned


def _copy_candidates(planned: list[tuple[Candidate, Path]]) -> None:
    for candidate, target in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate.source, target)


def _write_manifest(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([candidate.to_dict() for candidate in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
