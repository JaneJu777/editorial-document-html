#!/usr/bin/env python3
"""Build the static GitHub Pages gallery into _site/."""

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
STYLES = ("editorial", "newsroom", "humanist-blog", "notebook")


def render_previews():
    preview_dir = SITE / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    shared_fonts = SITE / "assets" / "fonts"
    shared_fonts.mkdir(parents=True, exist_ok=True)

    for style in STYLES:
        output = preview_dir / f"{style}-preview.html"
        subprocess.run([
            sys.executable,
            str(ROOT / "scripts" / "render_article.py"),
            str(ROOT / "examples" / f"{style}-preview.json"),
            str(output),
            "--style",
            style,
        ], check=True)

        asset_dir = preview_dir / f"{style}-preview-assets"
        for font in (asset_dir / "fonts").glob("*.ttf"):
            target = shared_fonts / font.name
            if not target.exists():
                shutil.copy2(font, target)

        markup = output.read_text(encoding="utf-8")
        markup = markup.replace(f"{style}-preview-assets/fonts", "../assets/fonts")
        output.write_text(markup, encoding="utf-8")
        shutil.rmtree(asset_dir)


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    for name in ("index.html", "gallery.css", "gallery.js", "demo-recorder.html"):
        shutil.copy2(ROOT / "gallery" / name, SITE / name)

    shutil.copytree(ROOT / "gallery" / "vendor", SITE / "vendor")

    source_screens = ROOT / "gallery" / "assets" / "screenshots"
    if source_screens.exists():
        shutil.copytree(source_screens, SITE / "assets" / "screenshots")

    demo_video = ROOT / "gallery" / "assets" / "editorial-document-html-demo.webm"
    if demo_video.exists():
        shutil.copy2(demo_video, SITE / "assets" / demo_video.name)

    shutil.copy2(ROOT / "gallery" / "source.md", SITE / "source.md")
    (SITE / ".nojekyll").touch()
    render_previews()
    print(SITE.resolve())


if __name__ == "__main__":
    main()
