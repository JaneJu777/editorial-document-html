#!/usr/bin/env python3
"""Build the four style-matched preview pages from their dedicated fixtures."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLES = ("editorial", "newsroom", "humanist-blog", "notebook")


def main():
    preview_dir = ROOT / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for style in STYLES:
        source = ROOT / "examples" / f"{style}-preview.json"
        output = preview_dir / f"{style}-preview.html"
        subprocess.run([
            sys.executable,
            str(ROOT / "scripts" / "render_article.py"),
            str(source),
            str(output),
            "--style",
            style,
        ], check=True)


if __name__ == "__main__":
    main()
