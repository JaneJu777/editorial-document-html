#!/usr/bin/env python3
"""Validate editorial-document-html article JSON with actionable path errors."""

import argparse
import json
from pathlib import Path


CANONICAL_STYLES = {"editorial", "newsroom", "humanist-blog", "notebook"}
STYLE_ALIASES = {"claude-blog": "humanist-blog"}
STYLES = CANONICAL_STYLES | set(STYLE_ALIASES)
BLOCK_TYPES = {
    "paragraph", "list", "heading", "cards", "compare", "keyvalue", "aside",
    "callout", "links", "table", "flow", "image", "quote", "code",
}
CHIP_TONES = {"high", "medium-high", "medium", "low", "p0", "p1", "p2", "later"}
CARD_TONES = {"surface", "tint", "ink", "accent"}
COMPARE_TONES = {"old", "neutral", "new", "accent"}


class ArticleValidationError(ValueError):
    pass


def normalize_style(style):
    """Return the public style name while accepting pre-2.1 legacy input."""
    return STYLE_ALIASES.get(style, style)


def fail(path, message):
    raise ArticleValidationError(f"{path}: {message}")


def require_text(value, path, *, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        fail(path, "expected non-empty text")


def validate_inline(value, path):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for index, part in enumerate(value):
            validate_inline(part, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        require_text(value.get("text"), f"{path}.text", allow_empty=True)
        unknown = set(value) - {"text", "bold", "href"}
        if unknown:
            fail(path, f"unknown inline keys: {', '.join(sorted(unknown))}")
        if "bold" in value and not isinstance(value["bold"], bool):
            fail(f"{path}.bold", "expected boolean")
        if "href" in value:
            require_text(value["href"], f"{path}.href")
        return
    fail(path, "expected text, inline run, or inline-run array")


def validate_blocks(blocks, path):
    if not isinstance(blocks, list):
        fail(path, "expected an array of blocks")
    for index, block in enumerate(blocks):
        validate_block(block, f"{path}[{index}]")


def validate_body(item, path):
    if "blocks" in item:
        validate_blocks(item["blocks"], f"{path}.blocks")
    elif "content" in item:
        validate_inline(item["content"], f"{path}.content")
    else:
        fail(path, "expected content or blocks")


def validate_list_item(item, path):
    if isinstance(item, (str, list)):
        validate_inline(item, path)
    elif isinstance(item, dict):
        validate_inline(item.get("content", ""), f"{path}.content")
        if "children" in item:
            if not isinstance(item["children"], list):
                fail(f"{path}.children", "expected an array")
            for index, child in enumerate(item["children"]):
                validate_list_item(child, f"{path}.children[{index}]")
    else:
        fail(path, "invalid list item")


def validate_block(block, path):
    if not isinstance(block, dict):
        fail(path, "expected an object")
    kind = block.get("type")
    if kind not in BLOCK_TYPES:
        fail(f"{path}.type", f"unknown block type {kind!r}")
    if kind == "paragraph":
        validate_inline(block.get("content", ""), f"{path}.content")
    elif kind == "heading":
        require_text(block.get("text"), f"{path}.text")
    elif kind == "list":
        items = block.get("items")
        if not isinstance(items, list) or not items:
            fail(f"{path}.items", "expected at least one item")
        for index, item in enumerate(items):
            validate_list_item(item, f"{path}.items[{index}]")
    elif kind == "cards":
        items = block.get("items")
        if not isinstance(items, list) or not 2 <= len(items) <= 5:
            fail(f"{path}.items", "cards require 2 to 5 items")
        for index, item in enumerate(items):
            item_path = f"{path}.items[{index}]"
            require_text(item.get("title"), f"{item_path}.title")
            if "icon" in item:
                require_text(item["icon"], f"{item_path}.icon")
            if item.get("tone") not in CARD_TONES | {None}:
                fail(f"{item_path}.tone", "unknown card tone")
            validate_body(item, item_path)
    elif kind == "compare":
        columns = block.get("columns")
        if not isinstance(columns, list) or not 2 <= len(columns) <= 3:
            fail(f"{path}.columns", "compare requires 2 or 3 columns")
        require_text(block.get("label"), f"{path}.label")
        for index, column in enumerate(columns):
            column_path = f"{path}.columns[{index}]"
            require_text(column.get("label"), f"{column_path}.label")
            if column.get("tone") not in COMPARE_TONES | {None}:
                fail(f"{column_path}.tone", "unknown compare tone")
            validate_body(column, column_path)
    elif kind == "keyvalue":
        rows = block.get("rows")
        if not isinstance(rows, list) or not rows:
            fail(f"{path}.rows", "expected at least one row")
        for index, row in enumerate(rows):
            row_path = f"{path}.rows[{index}]"
            require_text(row.get("label"), f"{row_path}.label")
            validate_body(row, row_path)
    elif kind in {"aside", "callout"}:
        if kind == "callout" and block.get("tone", "neutral") not in {"neutral", "ink"}:
            fail(f"{path}.tone", "unknown callout tone")
        validate_body(block, path)
        if block.get("action"):
            require_text(block["action"].get("label"), f"{path}.action.label")
            require_text(block["action"].get("href"), f"{path}.action.href")
    elif kind == "links":
        items = block.get("items")
        if not isinstance(items, list) or not items:
            fail(f"{path}.items", "expected at least one link item")
        for index, item in enumerate(items):
            require_text(item.get("title"), f"{path}.items[{index}].title")
    elif kind == "table":
        headers, rows = block.get("headers"), block.get("rows")
        require_text(block.get("label"), f"{path}.label")
        if not isinstance(headers, list) or not headers:
            fail(f"{path}.headers", "expected at least one header")
        for index, header in enumerate(headers):
            validate_inline(header, f"{path}.headers[{index}]")
        if not isinstance(rows, list):
            fail(f"{path}.rows", "expected an array")
        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != len(headers):
                fail(f"{path}.rows[{row_index}]", "column count must match headers")
            for cell_index, cell in enumerate(row):
                cell_path = f"{path}.rows[{row_index}][{cell_index}]"
                if isinstance(cell, dict) and "chip" in cell:
                    if cell["chip"] not in CHIP_TONES:
                        fail(f"{cell_path}.chip", "unknown chip tone")
                    validate_inline(cell.get("text", ""), f"{cell_path}.text")
                else:
                    validate_inline(cell, cell_path)
    elif kind == "flow":
        steps = block.get("steps")
        require_text(block.get("label"), f"{path}.label")
        if not isinstance(steps, list) or len(steps) < 2:
            fail(f"{path}.steps", "flow requires at least two steps")
        for index, step in enumerate(steps):
            validate_inline(step.get("title", ""), f"{path}.steps[{index}].title")
    elif kind == "image":
        require_text(block.get("src"), f"{path}.src")
        require_text(block.get("alt"), f"{path}.alt")
    elif kind == "quote":
        validate_inline(block.get("content", ""), f"{path}.content")
    elif kind == "code":
        require_text(block.get("text"), f"{path}.text", allow_empty=True)
        if "language" in block:
            require_text(block["language"], f"{path}.language")


def validate_article(article, path="article"):
    if not isinstance(article, dict):
        fail(path, "expected an object")
    require_text(article.get("title"), f"{path}.title")
    style = article.get("style", "editorial")
    if style not in STYLES:
        fail(f"{path}.style", f"expected one of {', '.join(sorted(CANONICAL_STYLES))}")
    require_text(article.get("language", "en"), f"{path}.language")
    chapters = article.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        fail(f"{path}.chapters", "expected at least one chapter")
    for chapter_index, chapter in enumerate(chapters):
        chapter_path = f"{path}.chapters[{chapter_index}]"
        require_text(chapter.get("title"), f"{chapter_path}.title")
        validate_blocks(chapter.get("blocks", []), f"{chapter_path}.blocks")
        sections = chapter.get("sections", [])
        if not isinstance(sections, list):
            fail(f"{chapter_path}.sections", "expected an array")
        for section_index, section in enumerate(sections):
            section_path = f"{chapter_path}.sections[{section_index}]"
            require_text(section.get("title"), f"{section_path}.title")
            validate_blocks(section.get("blocks", []), f"{section_path}.blocks")
    translations = article.get("translations", {})
    if not isinstance(translations, dict):
        fail(f"{path}.translations", "expected an object")
    for code, translation in translations.items():
        validate_article({**translation, "style": style, "translations": {}}, f"{path}.translations.{code}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article_json", type=Path)
    args = parser.parse_args()
    data = json.loads(args.article_json.read_text(encoding="utf-8"))
    validate_article(data)
    print(f"valid: {args.article_json.resolve()}")


if __name__ == "__main__":
    main()
