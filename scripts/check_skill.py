#!/usr/bin/env python3
"""Run deterministic validation, rendering, and behavior tests for this skill."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_article import validate_article


ROOT = Path(__file__).resolve().parents[1]
SYNC_PATHS = ["SKILL.md", "assets", "examples", "references", "scripts", "tests"]
STYLES = ("editorial", "newsroom", "humanist-blog", "notebook")


def compare_installed(installed):
    differences = []
    for relative in SYNC_PATHS:
        source = ROOT / relative
        target = installed / relative
        if source.is_file():
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                differences.append(relative)
        elif source.is_dir():
            source_files = {path.relative_to(source) for path in source.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            target_files = ({path.relative_to(target) for path in target.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
                            if target.is_dir() else set())
            if source_files != target_files or any((source / path).read_bytes() != (target / path).read_bytes()
                                                   for path in source_files & target_files):
                differences.append(relative)
    if differences:
        raise SystemExit("installed skill differs: " + ", ".join(differences))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, help="Also verify an installed skill copy")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        titles = set()
        for style in STYLES:
            sample = ROOT / "examples" / f"{style}-preview.json"
            data = json.loads(sample.read_text(encoding="utf-8"))
            validate_article(data)
            if data.get("style") != style:
                raise SystemExit(f"preview fixture style mismatch: {sample}")
            titles.add(data["title"])
            output = Path(directory) / f"{style}.html"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "render_article.py"),
                            str(sample), str(output), "--style", style], check=True)
            markup = output.read_text(encoding="utf-8")
            if f'data-style="{style}"' not in markup:
                raise SystemExit(f"rendered style mismatch: {style}")
        if len(titles) != len(STYLES):
            raise SystemExit("preview fixtures must use distinct, style-matched content")
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")], check=True)
    if args.installed:
        compare_installed(args.installed)
    print("skill checks passed")


if __name__ == "__main__":
    main()
