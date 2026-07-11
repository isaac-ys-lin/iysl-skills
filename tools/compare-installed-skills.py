#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path


IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def included_files(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_NAMES for part in path.relative_to(root).parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_skills", type=Path)
    parser.add_argument("installed_skills", type=Path)
    args = parser.parse_args()

    expected_names = sorted(path.name for path in args.source_skills.iterdir() if path.is_dir())
    actual_names = sorted(path.name for path in args.installed_skills.iterdir() if path.is_dir())
    if actual_names != expected_names:
        raise SystemExit(
            f"installed skill inventory mismatch: expected={expected_names} actual={actual_names}"
        )

    failures = []
    for name in expected_names:
        expected = included_files(args.source_skills / name)
        actual = included_files(args.installed_skills / name)
        if expected != actual:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            changed = sorted(
                path for path in set(expected) & set(actual) if expected[path] != actual[path]
            )
            failures.append(
                f"{name}: missing={missing} extra={extra} changed={changed}"
            )

    if failures:
        raise SystemExit("install parity failed:\n" + "\n".join(failures))

    print(f"install parity verified for {len(expected_names)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
