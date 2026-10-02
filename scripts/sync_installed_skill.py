#!/usr/bin/env python3
"""Synchronize this project skill into a Codex skills directory."""

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC_PATHS = ["SKILL.md", "assets", "examples", "references", "scripts", "tests"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path,
                        help="Installed skill folder, e.g. ~/.codex/skills/editorial-document-html")
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.name != "editorial-document-html":
        raise SystemExit("Refusing to sync: destination folder must be named editorial-document-html")
    destination.mkdir(parents=True, exist_ok=True)
    for relative in SYNC_PATHS:
        source = ROOT / relative
        target = destination / relative
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    print(destination)


if __name__ == "__main__":
    main()
