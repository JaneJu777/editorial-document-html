#!/usr/bin/env python3
"""Infer article structure and semantic components from Markdown, text, or DOCX.

The mapper is intentionally conservative: strong structural or lexical evidence creates
special components; ambiguous material remains a paragraph. A mapping report records
each decision so the result can be reviewed without asking the source author to label it.
"""

import argparse
import json
import re
from pathlib import Path

from extract_source import extract_docx
from validate_article import STYLES, normalize_style, validate_article


HEADING_END = set("。！？!?；;，,")
FLOW_CONTEXT = ("流程", "步骤", "阶段", "过程", "生命周期", "工作流", "how it works", "workflow", "process", "steps")
COMPARE_CONTEXT = ("比较", "对比", "差异", "取舍", "versus", " vs ", "compare", "comparison")
KEY_LABELS = ("条件", "设施", "方式", "标准", "负责人", "时间", "日期", "状态", "版本", "范围", "目标", "输入", "输出", "依赖", "指标", "频率")
CALLOUT_PREFIXES = ("结论", "关键结论", "重点", "注意", "建议", "警告", "结论是", "recommendation", "warning", "important")
ASIDE_PREFIXES = ("补充", "说明", "备注", "背景", "旁注", "note", "context")
URL_RE = re.compile(r"https?://[^\s)]+")
HEADING_NUMBER_RE = re.compile(r"^(?:第[一二三四五六七八九十百]+[章节部分]|\d+(?:\.\d+)*[、.\s]+)\S")
LIST_RE = re.compile(r"^(\s*)(?:(\d+)[.)、]|[-*+•])\s+(.+)$")
PAIR_RE = re.compile(r"^\s*([^：:\t]{1,18})[：:\t]\s*(.+)$")
MD_LINK_RE = re.compile(r"(!?)\[([^\]]+)\]\(([^)]+)\)")
MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
CHIP_VALUES = {
    "高": "high", "中高": "medium-high", "中": "medium", "低": "low",
    "high": "high", "medium high": "medium-high", "medium": "medium", "low": "low",
    "p0": "p0", "p1": "p1", "p2": "p2", "稍后": "later", "later": "later",
}


def inline_markdown(text):
    """Convert simple Markdown links and bold spans to renderer inline runs."""
    runs = []
    cursor = 0
    matches = []
    for match in MD_LINK_RE.finditer(text):
        if not match.group(1):
            matches.append((match.start(), match.end(), {"text": match.group(2), "href": match.group(3)}))
    for match in MD_BOLD_RE.finditer(text):
        matches.append((match.start(), match.end(), {"text": match.group(1) or match.group(2), "bold": True}))
    for start, end, run in sorted(matches):
        if start < cursor:
            continue
        if start > cursor:
            runs.append(text[cursor:start])
        runs.append(run)
        cursor = end
    if cursor < len(text):
        runs.append(text[cursor:])
    return runs if any(isinstance(run, dict) for run in runs) else text


def split_pipe_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_pipe_separator(line):
    cells = split_pipe_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def heading_score(text):
    value = text.strip()
    if not value or len(value) > 42 or URL_RE.search(value) or PAIR_RE.match(value):
        return 0
    score = 0
    if len(value) <= 24:
        score += 2
    if value[-1] not in HEADING_END:
        score += 1
    if HEADING_NUMBER_RE.match(value):
        score += 2
    if re.search(r"[。！？!?；;]", value):
        score -= 2
    if len(value.split()) <= 8:
        score += 1
    return score


def nested_list(entries):
    """Turn (indent, ordered, value) entries into renderer list items."""
    if not entries:
        return False, []
    indents = sorted({entry[0] for entry in entries})
    rank = {indent: index for index, indent in enumerate(indents)}
    normalized = [(rank[indent], ordered, value) for indent, ordered, value in entries]

    def consume(index, level, ordered):
        items = []
        while index < len(normalized):
            item_level, item_ordered, value = normalized[index]
            if item_level < level or (item_level == level and item_ordered != ordered):
                break
            if item_level > level and items:
                children, index = consume(index, item_level, item_ordered)
                previous = items.pop()
                items.append({"content": previous, "children": children, "ordered": item_ordered})
                continue
            items.append(value)
            index += 1
        return items, index

    ordered = normalized[0][1]
    items, _ = consume(0, normalized[0][0], ordered)
    return ordered, items


def parse_markdown(path):
    lines = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    tokens = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = re.match(r"^\s*```([^`]*)$", line)
        if fence:
            language = fence.group(1).strip()
            index += 1
            body = []
            while index < len(lines) and not re.match(r"^\s*```", lines[index]):
                body.append(lines[index])
                index += 1
            index += index < len(lines)
            tokens.append({"kind": "code", "text": "\n".join(body), "language": language})
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            tokens.append({"kind": "heading", "level": len(heading.group(1)), "text": heading.group(2).strip(), "explicit": True})
            index += 1
            continue
        if index + 1 < len(lines) and "|" in line and is_pipe_separator(lines[index + 1]):
            headers = split_pipe_row(line)
            index += 2
            rows = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                row = split_pipe_row(lines[index])
                if len(row) == len(headers):
                    rows.append(row)
                index += 1
            tokens.append({"kind": "table", "headers": headers, "rows": rows})
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[index]))
                index += 1
            tokens.append({"kind": "quote", "text": " ".join(quote)})
            continue
        image = re.fullmatch(r"\s*!\[([^\]]*)\]\(([^)]+)\)\s*", line)
        if image:
            tokens.append({"kind": "image", "alt": image.group(1) or path.stem, "src": image.group(2)})
            index += 1
            continue
        item = LIST_RE.match(line)
        if item:
            entries = []
            while index < len(lines):
                current = LIST_RE.match(lines[index])
                if not current:
                    break
                indent = len(current.group(1).expandtabs(4))
                entries.append((indent, bool(current.group(2)), inline_markdown(current.group(3).strip())))
                index += 1
            ordered, items = nested_list(entries)
            tokens.append({"kind": "list", "ordered": ordered, "items": items})
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip():
            if (re.match(r"^(#{1,6})\s+", lines[index]) or LIST_RE.match(lines[index])
                    or lines[index].lstrip().startswith(">") or re.match(r"^\s*```", lines[index])):
                break
            paragraph.append(lines[index].strip())
            index += 1
        tokens.extend(classify_unmarked_lines(paragraph))
    return tokens


def classify_unmarked_lines(lines):
    clean = [line.strip() for line in lines if line.strip()]
    if not clean:
        return []
    if len(clean) == 1 and heading_score(clean[0]) >= 4:
        return [{"kind": "heading", "level": 2, "text": clean[0], "explicit": False}]
    pairs = [PAIR_RE.match(line) for line in clean]
    if len(clean) >= 2 and all(pairs):
        return [{"kind": "pairs", "pairs": [(match.group(1).strip(), match.group(2).strip()) for match in pairs]}]
    if len(clean) >= 2 and all(URL_RE.search(line) for line in clean):
        return [{"kind": "links", "lines": clean}]
    if len(clean) >= 2 and all("\t" in line for line in clean):
        matrix = [[cell.strip() for cell in line.split("\t")] for line in clean]
        if len({len(row) for row in matrix}) == 1 and len(matrix[0]) >= 2:
            return [{"kind": "table", "headers": matrix[0], "rows": matrix[1:]}]
    return [{"kind": "paragraph", "text": " ".join(clean)}]


def parse_text(path):
    groups = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
    tokens = []
    for group in groups:
        lines = [line for line in group.split("\n") if line.strip()]
        if not lines:
            continue
        list_matches = [LIST_RE.match(line) for line in lines]
        if all(list_matches):
            entries = [(len(match.group(1).expandtabs(4)), bool(match.group(2)), match.group(3).strip())
                       for match in list_matches]
            ordered, items = nested_list(entries)
            tokens.append({"kind": "list", "ordered": ordered, "items": items})
        else:
            tokens.extend(classify_unmarked_lines(lines))
    return tokens


def parse_docx(path, media_dir):
    inventory = extract_docx(path, media_dir)
    tokens = []
    for block in inventory["blocks"]:
        if block["type"] == "table":
            rows = block.get("rows", [])
            if rows:
                tokens.append({"kind": "table", "headers": rows[0], "rows": rows[1:]})
            continue
        text = block.get("text", "").strip()
        if text:
            style = (block.get("style") or "").lower()
            heading = re.search(r"heading\s*([1-6])|标题\s*([1-6])", style)
            if heading:
                level = int(heading.group(1) or heading.group(2))
                tokens.append({"kind": "heading", "level": level, "text": text, "explicit": True})
            elif any(name in style for name in ("quote", "引用")):
                tokens.append({"kind": "quote", "text": text})
            elif any(name in style for name in ("code", "代码")):
                tokens.append({"kind": "code", "text": text, "language": ""})
            elif block.get("list"):
                tokens.append({"kind": "list-item", "ordered": block["list"].get("ordered", False),
                               "level": block["list"].get("level", 0), "text": block.get("runs") or text})
            else:
                inferred = classify_unmarked_lines(text.split("\n"))
                if len(inferred) == 1 and inferred[0]["kind"] == "paragraph" and block.get("runs"):
                    inferred[0]["inline"] = block["runs"]
                tokens.extend(inferred)
        for image in block.get("images", []):
            tokens.append({"kind": "image", "src": image["src"], "alt": image["alt"]})
    grouped = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token["kind"] == "list-item":
            entries = []
            while index < len(tokens) and tokens[index]["kind"] == "list-item":
                current = tokens[index]
                entries.append((current["level"], current["ordered"], current["text"]))
                index += 1
            ordered, items = nested_list(entries)
            grouped.append({"kind": "list", "ordered": ordered, "items": items})
        else:
            grouped.append(token)
            index += 1
    return grouped


def strip_prefix(text, prefixes):
    lower = text.lower()
    for prefix in prefixes:
        if lower.startswith(prefix.lower()):
            return text[len(prefix):].lstrip("：: -—") or text
    return text


def map_token(token, context, report):
    kind = token["kind"]
    if kind == "paragraph":
        text = token["text"]
        prefix = text.split("：", 1)[0].split(":", 1)[0].strip().lower()
        if any(prefix == value.lower() for value in CALLOUT_PREFIXES):
            report.append({"source": "paragraph", "component": "callout", "confidence": 0.9,
                           "reason": "recognized conclusion/warning lead-in"})
            return {"type": "callout", "label": prefix, "content": inline_markdown(strip_prefix(text, CALLOUT_PREFIXES))}
        if any(prefix == value.lower() for value in ASIDE_PREFIXES):
            report.append({"source": "paragraph", "component": "aside", "confidence": 0.88,
                           "reason": "recognized supporting-note lead-in"})
            return {"type": "aside", "label": prefix, "content": inline_markdown(strip_prefix(text, ASIDE_PREFIXES)), "layout": "stacked"}
        report.append({"source": "paragraph", "component": "paragraph", "confidence": 1.0,
                       "reason": "ambiguous prose remains prose"})
        return {"type": "paragraph", "content": token.get("inline", inline_markdown(text))}
    if kind == "pairs":
        pairs = token["pairs"]
        context_lower = context.lower()
        if 2 <= len(pairs) <= 3 and any(word in context_lower for word in COMPARE_CONTEXT):
            columns = []
            for label, value in pairs:
                label_lower = label.lower()
                tone = "old" if any(word in label_lower for word in ("传统", "旧", "before", "old")) else (
                    "new" if any(word in label_lower for word in ("原生", "新", "after", "new", "推荐")) else "neutral")
                columns.append({"label": label, "tone": tone, "content": inline_markdown(value)})
            report.append({"source": "parallel label-value lines", "component": "compare", "confidence": 0.88,
                           "reason": "two or three alternatives appear under a comparison-oriented heading"})
            return {"type": "compare", "label": context, "columns": columns}
        key_like = sum(any(word in label.lower() for word in KEY_LABELS) for label, _ in pairs)
        if key_like >= max(1, len(pairs) // 2):
            component = {"type": "keyvalue", "rows": [{"label": label, "content": inline_markdown(value)} for label, value in pairs]}
            reason, confidence = "labels describe properties or operating metadata", 0.86
        elif 2 <= len(pairs) <= 5 and all(len(label) <= 14 for label, _ in pairs):
            component = {"type": "cards", "items": [{"title": label, "content": inline_markdown(value)} for label, value in pairs]}
            reason, confidence = "parallel short labels with explanatory bodies", 0.78
        else:
            component = {"type": "paragraph", "content": " ".join(f"{label}：{value}" for label, value in pairs)}
            reason, confidence = "pair pattern was not strong enough for a special component", 0.55
        report.append({"source": "label-value lines", "component": component["type"], "confidence": confidence, "reason": reason})
        return component
    if kind == "list":
        context_lower = context.lower()
        flat_items = all(not isinstance(item, dict) for item in token["items"])
        if token.get("ordered") and flat_items and len(token["items"]) >= 2 and any(word in context_lower for word in FLOW_CONTEXT):
            report.append({"source": "ordered list", "component": "flow", "confidence": 0.9,
                           "reason": "ordered items appear under a process-oriented heading"})
            return {"type": "flow", "label": context or "流程", "steps": [{"title": item} for item in token["items"]]}
        report.append({"source": "list", "component": "list", "confidence": 0.98,
                       "reason": "list structure is explicit or strongly patterned"})
        return {"type": "list", "ordered": bool(token.get("ordered")), "items": token["items"]}
    if kind == "table":
        report.append({"source": "tabular rows", "component": "table", "confidence": 0.98,
                       "reason": "consistent row and column structure"})
        rows = []
        for row in token["rows"]:
            mapped = []
            for index, cell in enumerate(row):
                tone = CHIP_VALUES.get(cell.strip().lower()) if isinstance(cell, str) and index > 0 else None
                mapped.append({"text": cell, "chip": tone} if tone else cell)
            rows.append(mapped)
        return {"type": "table", "label": context or "数据表", "headers": token["headers"],
                "rows": rows, "first_column_header": True}
    if kind == "quote":
        report.append({"source": "blockquote", "component": "quote", "confidence": 1.0,
                       "reason": "quotation syntax is explicit"})
        return {"type": "quote", "content": inline_markdown(token["text"])}
    if kind == "code":
        report.append({"source": "fenced code", "component": "code", "confidence": 1.0,
                       "reason": "code fence is explicit"})
        block = {"type": "code", "text": token["text"]}
        if token.get("language"):
            block["language"] = token["language"]
        return block
    if kind == "image":
        report.append({"source": "image", "component": "image", "confidence": 1.0,
                       "reason": "image syntax is explicit"})
        return {"type": "image", "src": token["src"], "alt": token["alt"]}
    if kind == "links":
        items = []
        for line in token["lines"]:
            url = URL_RE.search(line).group(0)
            title = line.replace(url, "").strip(" -—：:") or url
            items.append({"title": title, "href": url})
        report.append({"source": "URL list", "component": "links", "confidence": 0.95,
                       "reason": "multiple standalone destinations"})
        return {"type": "links", "items": items}
    raise ValueError(f"Cannot map token: {kind}")


def infer_article(source, style="editorial", language="zh-CN", title_override=None):
    style = normalize_style(style)
    suffix = source.suffix.lower()
    media_dir = source.parent / f"{source.stem}-media"
    if suffix in {".md", ".markdown"}:
        tokens = parse_markdown(source)
    elif suffix == ".txt":
        tokens = parse_text(source)
    elif suffix == ".docx":
        tokens = parse_docx(source, media_dir)
    else:
        raise ValueError(f"Unsupported source: {suffix}")
    if not tokens:
        raise ValueError("Source contains no readable content")

    title = title_override
    if not title:
        for index, token in enumerate(tokens):
            if token["kind"] == "heading" and token.get("level") == 1:
                title = token["text"]
                tokens.pop(index)
                break
    if not title and tokens and tokens[0]["kind"] in {"heading", "paragraph"}:
        candidate = tokens[0].get("text", "")
        if heading_score(candidate) >= 3:
            title = candidate
            tokens.pop(0)
    title = title or source.stem.replace("_", " ").replace("-", " ").strip()

    headings = [token for token in tokens if token["kind"] == "heading"]
    chapter_level = min((token.get("level", 2) for token in headings), default=None)
    section_level = chapter_level + 1 if chapter_level else None
    chapters = []
    current_chapter = None
    current_section = None
    report = []

    def ensure_chapter():
        nonlocal current_chapter
        if current_chapter is None:
            current_chapter = {"title": "正文", "blocks": [], "sections": []}
            chapters.append(current_chapter)
            report.append({"source": "document structure", "component": "chapter", "confidence": 0.5,
                           "reason": "no reliable chapter heading; generated neutral container title"})

    for token in tokens:
        if token["kind"] == "heading":
            if token.get("level", 2) <= chapter_level:
                current_chapter = {"title": token["text"], "blocks": [], "sections": []}
                chapters.append(current_chapter)
                current_section = None
                report.append({"source": "heading", "component": "chapter", "confidence": 1.0 if token.get("explicit") else 0.76,
                               "reason": "highest remaining heading level"})
            elif section_level and token.get("level", 3) <= section_level:
                ensure_chapter()
                current_section = {"title": token["text"], "blocks": []}
                current_chapter["sections"].append(current_section)
                report.append({"source": "heading", "component": "section", "confidence": 1.0 if token.get("explicit") else 0.74,
                               "reason": "next heading level below chapter"})
            else:
                ensure_chapter()
                target = current_section["blocks"] if current_section else current_chapter["blocks"]
                target.append({"type": "heading", "text": token["text"]})
                report.append({"source": "heading", "component": "heading", "confidence": 0.92,
                               "reason": "heading is below section level"})
            continue
        ensure_chapter()
        context = current_section["title"] if current_section else current_chapter["title"]
        block = map_token(token, context, report)
        target = current_section["blocks"] if current_section else current_chapter["blocks"]
        target.append(block)

    for chapter in chapters:
        if not chapter["sections"]:
            chapter.pop("sections")
    article = {"style": style, "language": language, "title": title, "chapters": chapters,
               "mapping_report": report}
    validate_article(article)
    return article


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--style", choices=sorted(STYLES), default="editorial",
                        help="Presentation style; claude-blog is a deprecated alias for humanist-blog")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--title", help="Optional override when the source has no reliable title")
    args = parser.parse_args()
    article = infer_article(args.source, args.style, args.language, args.title)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output_json.resolve())


if __name__ == "__main__":
    main()
