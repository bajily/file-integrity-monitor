"""Create and compare offline SHA-256 file-integrity baselines."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def snapshot(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")
    files, skipped = {}, []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            skipped.append(relative)
            continue
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        files[relative] = digest.hexdigest()
    return {"version": 1, "algorithm": "sha256", "files": files, "skipped_symlinks": skipped}


def validate(baseline: dict) -> None:
    if not isinstance(baseline, dict) or baseline.get("version") != 1 or baseline.get("algorithm") != "sha256":
        raise ValueError("unsupported baseline format")
    files = baseline.get("files")
    if not isinstance(files, dict):
        raise ValueError("baseline files must be an object")
    for path, digest in files.items():
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("baseline contains an invalid relative path")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("baseline contains an invalid SHA-256 digest")


def compare(baseline: dict, current: dict) -> dict:
    validate(baseline)
    validate(current)
    before, after = baseline["files"], current["files"]
    report = {"added": sorted(after.keys() - before.keys()),
              "removed": sorted(before.keys() - after.keys()),
              "modified": sorted(path for path in before.keys() & after.keys()
                                 if before[path] != after[path]),
              "skipped_symlinks": current.get("skipped_symlinks", [])}
    report["changed"] = any(report[key] for key in ("added", "removed", "modified"))
    return report


def external_baseline(root: Path, baseline: Path) -> None:
    if baseline.resolve().is_relative_to(root.resolve()):
        raise ValueError("store the baseline outside the monitored directory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["baseline", "check"])
    parser.add_argument("root", type=Path)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()
    try:
        external_baseline(args.root, args.baseline)
        if args.command == "baseline":
            content = json.dumps(snapshot(args.root), indent=2) + "\n"
            with args.baseline.open("x", encoding="utf-8") as stream:
                stream.write(content)
            print(json.dumps({"baseline_created": str(args.baseline)}))
            return 0
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        report = compare(baseline, snapshot(args.root))
        print(json.dumps(report, indent=2))
        return 1 if report["changed"] else 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
