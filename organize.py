"""Preview or copy top-level files into extension-based categories."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

CATEGORIES = {
    "documents": {".pdf", ".docx", ".txt", ".md", ".odt"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"},
    "data": {".csv", ".json", ".xlsx", ".tsv", ".yaml", ".yml"},
    "archives": {".zip", ".tar", ".gz", ".7z"},
    "code": {".py", ".js", ".ts", ".html", ".css", ".sh"},
}


def plan(source: Path, destination: Path) -> list[dict]:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("source must be a directory")
    if destination.is_symlink():
        raise ValueError("destination must not be a symbolic link")
    destination = destination.resolve()
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("source and destination must be separate, non-nested directories")
    if destination.exists() and not destination.is_dir():
        raise ValueError("destination must be a directory")
    operations = []
    for path in sorted(source.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        category = next((name for name, suffixes in CATEGORIES.items()
                         if path.suffix.lower() in suffixes), "other")
        target = destination / category / path.name
        if target.parent.is_symlink():
            raise ValueError(f"category directory is a symbolic link: {category}")
        if target.parent.exists() and not target.parent.is_dir():
            raise ValueError(f"category path is not a directory: {category}")
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"destination already exists: {category}/{path.name}")
        operations.append({"source": str(path), "destination": str(target), "category": category})
    return operations


def apply(operations: list[dict]) -> list[str]:
    copied = []
    for operation in operations:
        source, target = Path(operation["source"]), Path(operation["destination"])
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"source is no longer a regular file: {source.name}")
        if target.parent.is_symlink():
            raise ValueError("category directory became a symbolic link")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents an accidental overwrite even after planning.
        with source.open("rb") as incoming:
            with target.open("xb") as outgoing:
                try:
                    shutil.copyfileobj(incoming, outgoing)
                except BaseException:
                    outgoing.close()
                    target.unlink(missing_ok=True)
                    raise
        copied.append(str(target))
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--apply", action="store_true", help="copy files; default is a dry run")
    args = parser.parse_args()
    try:
        operations = plan(args.source, args.destination)
        copied = apply(operations) if args.apply else []
        print(json.dumps({"mode": "apply" if args.apply else "dry-run",
                          "planned": len(operations), "operations": operations,
                          "copied": copied}, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
