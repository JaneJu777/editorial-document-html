#!/usr/bin/env python3
"""Render a structured article JSON as one portable HTML file."""

import argparse
import base64
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from validate_article import STYLES, normalize_style, validate_article


ROOT = Path(__file__).resolve().parents[1]
CHIP_TONES = {"high", "medium-high", "medium", "low", "p0", "p1", "p2", "later"}
CARD_TONES = {"surface", "tint", "ink", "accent"}
COMPARE_TONES = {"old", "neutral", "new", "accent"}
CALLOUT_TONES = {"neutral", "ink"}
EDITORIAL_CARD_ICONS = (
    (("用户", "价值", "目标", "需求", "audience", "user", "goal"), "🎯"),
    (("业务", "增长", "收入", "杠杆", "growth", "business", "revenue"), "📈"),
    (("交付", "验收", "完成", "执行", "质量", "delivery", "quality"), "✅"),
    (("清晰", "可读", "观察", "clarity", "readability"), "👀"),
    (("克制", "平衡", "取舍", "balance", "trade-off"), "⚖️"),
    (("追溯", "来源", "证据", "链接", "source", "evidence", "trace"), "🔗"),
    (("安全", "合规", "风险", "security", "compliance", "risk"), "🛡️"),
    (("协作", "团队", "合作", "team", "collaboration"), "🤝"),
    (("数据", "分析", "指标", "data", "metric", "analysis"), "📊"),
    (("流程", "步骤", "路径", "process", "workflow"), "🧭"),
    (("创意", "想法", "机会", "idea", "opportunity"), "💡"),
)
BASE_FONTS = ["Inter-opsz-wght.ttf", "Newsreader-opsz-wght.ttf", "NotoSansSC-wght.ttf", "NotoSerifSC-wght.ttf"]
STYLE_FONTS = {
    "editorial": [],
    "humanist-blog": [],
    "newsroom": ["SourceSerif4-opsz-wght.ttf"],
    "notebook": ["PlaywriteUSModern-wght.ttf", "PlaywriteUSTrad-wght.ttf", "LXGWWenKai-Regular.ttf"],
}


def esc(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    url = str(value).strip()
    scheme = urlsplit(url).scheme.lower()
    return esc(url) if scheme in {"", "http", "https", "mailto"} and not url.startswith("//") else "#"


def inline(value):
    if isinstance(value, str):
        return esc(value)
    if isinstance(value, dict):
        content = esc(value.get("text", ""))
        if value.get("bold"):
            content = f"<strong>{content}</strong>"
        if value.get("href"):
            content = f'<a href="{safe_url(value["href"])}">{content}</a>'
        return content
    if isinstance(value, list):
        return "".join(inline(part) for part in value)
    return esc(value if value is not None else "")


def inline_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("text", ""))
    if isinstance(value, list):
        return "".join(inline_text(part) for part in value)
    return ""


def render_list(block):
    tag = "ol" if block.get("ordered") else "ul"
    items = []
    for item in block.get("items", []):
        if isinstance(item, dict) and "children" in item:
            nested = render_list({"ordered": item.get("ordered", False), "items": item["children"]})
            items.append(f"<li>{inline(item.get('content', ''))}{nested}</li>")
        else:
            items.append(f"<li>{inline(item)}</li>")
    return f'<{tag} class="article-list">{"".join(items)}</{tag}>'


def render_table(block):
    headers = block.get("headers", [])
    rows = block.get("rows", [])
    if not headers or any(len(row) != len(headers) for row in rows):
        raise ValueError(f"Table {block.get('label', '')!r} has inconsistent columns")
    first_col = bool(block.get("first_column_header"))
    head = "".join(f'<th scope="col">{inline(cell)}</th>' for cell in headers)
    body = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            tag = "th" if first_col and index == 0 else "td"
            scope = ' scope="row"' if tag == "th" else ""
            if isinstance(cell, dict) and "chip" in cell:
                tone = str(cell["chip"])
                if tone not in CHIP_TONES:
                    raise ValueError(f"Unknown chip tone: {tone}")
                content = f'<span class="chip chip-{tone}">{inline(cell.get("text", ""))}</span>'
            else:
                content = inline(cell)
            cells.append(f"<{tag}{scope}>{content}</{tag}>")
        body.append(f'<tr>{"".join(cells)}</tr>')
    sticky = " has-row-header" if first_col else ""
    label = esc(block.get("label", "Data table"))
    note = f'<p class="table-note">{inline(block["note"])}</p>' if block.get("note") else ""
    return (f'<div class="table-scroll" role="region" tabindex="0" aria-label="{label}">'
            f'<table class="article-table{sticky}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>{note}')


def render_flow(block):
    steps = block.get("steps", [])
    items = []
    for index, step in enumerate(steps, 1):
        note = f'<span class="flow-note">{inline(step["note"])}</span>' if step.get("note") else ""
        items.append(f'<li><span class="flow-index">{index:02d}</span>'
                     f'<span class="flow-copy"><strong>{inline(step.get("title", ""))}</strong>{note}</span></li>')
    loop = f'<p class="flow-loop">↻ {inline(block["loop"])}</p>' if block.get("loop") else ""
    return f'<figure class="flow" aria-label="{esc(block.get("label", "Process flow"))}"><ol>{"".join(items)}</ol>{loop}</figure>'


def card_label(value):
    """Micro label shown above a card title (uppercase in most styles)."""
    return f'<small class="card-label">{inline(value)}</small>' if value else ""


def block_body(block, style, *, content_key="content"):
    """Render a card body from child blocks, or from a single inline-run value."""
    if block.get("blocks"):
        return render_blocks(block["blocks"], style)
    if block.get(content_key):
        return f'<p>{inline(block[content_key])}</p>'
    return ""


def editorial_card_icon(card, style):
    if style != "editorial":
        return None
    if card.get("icon"):
        return card["icon"]
    semantic_text = " ".join((
        inline_text(card.get("title", "")),
        inline_text(card.get("label", "")),
        inline_text(card.get("content", "")),
        " ".join(inline_text(child.get("content", "")) for child in card.get("blocks", [])),
    )).lower()
    for keywords, icon in EDITORIAL_CARD_ICONS:
        if any(keyword in semantic_text for keyword in keywords):
            return icon
    return {"surface": "📄", "tint": "💡", "ink": "🌒", "accent": "✨"}.get(card.get("tone"), "📝")


def render_cards(block, style):
    cards = []
    for card in block.get("items", []):
        tone = card.get("tone")
        if tone and tone not in CARD_TONES:
            raise ValueError(f"Unknown card tone: {tone}")
        classes = "article-card" + (f" tone-{tone}" if tone else "")
        chosen_icon = editorial_card_icon(card, style)
        icon = f'<span class="card-icon" aria-hidden="true">{esc(chosen_icon)}</span> ' if chosen_icon else ""
        cards.append(f'<article class="{classes}">{card_label(card.get("label"))}'
                     f'<h4>{icon}{inline(card.get("title", ""))}</h4>{block_body(card, style)}</article>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


def render_compare(block, style):
    columns = block.get("columns", [])
    if not 2 <= len(columns) <= 3:
        raise ValueError("compare requires 2 or 3 columns")
    cells = []
    for column in columns:
        tone = column.get("tone")
        if tone and tone not in COMPARE_TONES:
            raise ValueError(f"Unknown compare tone: {tone}")
        cells.append(f'<div class="compare-card{" tone-" + tone if tone else ""}">'
                     f'{card_label(column.get("label"))}{block_body(column, style)}</div>')
    label = block.get("label")
    aria = f' role="group" aria-label="{esc(label)}"' if label else ""
    return (f'<div class="compare-grid" style="--compare-columns:{len(columns)}"{aria}>'
            f'{"".join(cells)}</div>')


def render_keyvalue(block, style):
    rows = []
    for row in block.get("rows", []):
        rows.append(f'<dt class="kv-key">{inline(row.get("label", ""))}</dt>'
                    f'<dd class="kv-value">{block_body(row, style)}</dd>')
    label = block.get("label")
    aria = f' aria-label="{esc(label)}"' if label else ""
    return f'<dl class="kv-list"{aria}>{"".join(rows)}</dl>'


def render_aside(block, style):
    label = card_label(block.get("label"))
    title = f'<h4>{inline(block["title"])}</h4>' if block.get("title") else ""
    meta = f'<i class="aside-meta">{inline(block["meta"])}</i>' if block.get("meta") else ""
    head = f'<div class="aside-head">{label}{title}{meta}</div>' if label or title or meta else ""
    stacked = " is-stacked" if block.get("layout") == "stacked" or not head else ""
    return f'<aside class="aside-card{stacked}">{head}<div class="aside-body">{block_body(block, style)}</div></aside>'


def render_callout(block, style):
    tone = block.get("tone", "neutral")
    if tone not in CALLOUT_TONES:
        raise ValueError(f"Unknown callout tone: {tone}")
    classes = "callout" + (f" tone-{tone}" if tone != "neutral" else "")
    body = f'{card_label(block.get("label"))}{block_body(block, style)}'
    action = block.get("action")
    if action:
        classes += " has-action"
        parts = (f'<div class="callout-copy">{body}</div>'
                 f'<a class="card-action" href="{safe_url(action.get("href", ""))}">'
                 f'{inline(action.get("label", ""))}</a>')
    else:
        parts = body
    aria = f' aria-label="{esc(block["label"])}"' if block.get("label") else ""
    return f'<div class="{classes}" role="note"{aria}>{parts}</div>'


def render_links(block):
    items = []
    for item in block.get("items", []):
        note = f'<small class="link-card-note">{inline(item["note"])}</small>' if item.get("note") else ""
        inner = f'<span class="link-card-title">{inline(item.get("title", ""))}</span>{note}'
        href = str(item.get("href", "")).strip()
        if href:
            items.append(f'<a class="link-card" href="{safe_url(href)}">{inner}</a>')
        else:
            items.append(f'<span class="link-card">{inner}</span>')
    return f'<div class="link-cards">{"".join(items)}</div>'


def render_blocks(blocks, style):
    output = []
    for block in blocks:
        kind = block.get("type")
        if kind == "paragraph":
            output.append(f'<p>{inline(block.get("content", ""))}</p>')
        elif kind == "heading":
            output.append(f'<h4>{inline(block.get("text", ""))}</h4>')
        elif kind == "list":
            output.append(render_list(block))
        elif kind == "cards":
            output.append(render_cards(block, style))
        elif kind == "compare":
            output.append(render_compare(block, style))
        elif kind == "keyvalue":
            output.append(render_keyvalue(block, style))
        elif kind == "aside":
            output.append(render_aside(block, style))
        elif kind == "callout":
            output.append(render_callout(block, style))
        elif kind == "links":
            output.append(render_links(block))
        elif kind == "table":
            output.append(render_table(block))
        elif kind == "flow":
            output.append(render_flow(block))
        elif kind == "image":
            caption = f'<figcaption>{inline(block["caption"])}</figcaption>' if block.get("caption") else ""
            output.append(f'<figure class="article-image"><img src="{safe_url(block.get("src", ""))}" '
                          f'alt="{esc(block.get("alt", ""))}" loading="lazy">{caption}</figure>')
        elif kind == "quote":
            cite = f'<cite>{inline(block["cite"])}</cite>' if block.get("cite") else ""
            output.append(f'<blockquote>{inline(block.get("content", ""))}{cite}</blockquote>')
        elif kind == "code":
            language = re.sub(r"[^a-zA-Z0-9_-]", "", str(block.get("language", "")))
            language_class = f' class="language-{esc(language)}"' if language else ""
            output.append(f'<pre><code{language_class}>{esc(block.get("text", ""))}</code></pre>')
        else:
            raise ValueError(f"Unknown block type: {kind}")
    return "\n".join(output)


def render_view(article, language, style):
    chapters = article.get("chapters", [])
    toc = []
    content = []
    for chapter_number, chapter in enumerate(chapters, 1):
        chapter_id = f"{language}-chapter-{chapter_number}"
        toc.append(f'<li><a href="#{chapter_id}">{esc(chapter_number):0>2} {inline(chapter.get("title", ""))}</a></li>')
        sections = []
        for section_number, section in enumerate(chapter.get("sections", []), 1):
            section_id = f"{chapter_id}-section-{section_number}"
            sections.append(f'<section id="{section_id}" class="article-section">'
                            f'<h3>{chapter_number}.{section_number} {inline(section.get("title", ""))}</h3>'
                            f'{render_blocks(section.get("blocks", []), style)}</section>')
        chapter_blocks = chapter.get("blocks", [])
        if style == "humanist-blog":
            chapter_summary = chapter.get("summary")
            if chapter_blocks and chapter_blocks[0].get("type") == "paragraph":
                opening_paragraph = chapter_blocks[0].get("content")
                if not chapter_summary:
                    chapter_summary = opening_paragraph
                    chapter_blocks = chapter_blocks[1:]
                elif opening_paragraph == chapter_summary:
                    chapter_blocks = chapter_blocks[1:]
            summary_html = (f'<p class="chapter-summary">{inline(chapter_summary)}</p>'
                            if chapter_summary else "")
            chapter_heading = (
                f'<header class="chapter-band chapter-band-{(chapter_number - 1) % 6 + 1}">'
                f'<span class="chapter-number">{chapter_number:02d}</span>'
                f'<div class="chapter-heading-copy"><h2>{inline(chapter.get("title", ""))}</h2>'
                f'{summary_html}</div></header>'
            )
        else:
            chapter_summary = chapter.get("summary")
            if (chapter_summary and chapter_blocks
                    and chapter_blocks[0].get("type") == "paragraph"
                    and chapter_blocks[0].get("content") == chapter_summary):
                chapter_blocks = chapter_blocks[1:]
            summary_html = (f'<p class="chapter-summary">{inline(chapter_summary)}</p>'
                            if chapter_summary else "")
            chapter_heading = (
                f'<h2><span>{chapter_number:02d}</span>{inline(chapter.get("title", ""))}</h2>'
                f'{summary_html}'
            )
        content.append(f'<section id="{chapter_id}" class="article-chapter">'
                       f'{chapter_heading}{render_blocks(chapter_blocks, style)}'
                       f'{"".join(sections)}</section>')
    meta = []
    if article.get("created_at"):
        date = esc(article["created_at"])
        meta.append(f'<time datetime="{date}">{date}</time>')
    if article.get("author"):
        meta.append(f'<span>{esc(article["author"])}</span>')
    meta_separator = '<span aria-hidden="true">·</span>'
    byline = f'<p class="byline">{meta_separator.join(meta)}</p>' if meta else ""
    summary = ""
    if article.get("summary"):
        note = '<span class="generated-label">Generated summary</span>' if article.get("summary_generated") else ""
        summary = f'<div class="summary">{note}<p>{inline(article["summary"])}</p></div>'
    eyebrow = f'<p class="eyebrow">{inline(article["eyebrow"])}</p>' if article.get("eyebrow") else ""
    return (f'<div class="language-view" data-language-view="{esc(language)}">'
            f'<main class="article-shell"><header class="article-hero">{eyebrow}'
            f'<h1>{inline(article.get("title", "Untitled"))}</h1>{byline}</header>{summary}'
            f'<div class="article-content">{"".join(content)}</div></main>'
            f'<nav class="toc" aria-label="On this page"><p>On this page</p><ol>{"".join(toc)}</ol></nav></div>')


def prepare_fonts(css, output_html, style, mode):
    font_names = BASE_FONTS + STYLE_FONTS[style]
    source_dir = ROOT / "assets" / "fonts"
    if mode == "embed":
        for name in font_names:
            payload = base64.b64encode((source_dir / name).read_bytes()).decode("ascii")
            css = css.replace(f"__FONT_DIR__/{name}", f"data:font/ttf;base64,{payload}")
        return css
    target_dir = output_html.parent / f"{output_html.stem}-assets" / "fonts"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in font_names:
        shutil.copy2(source_dir / name, target_dir / name)
    relative_dir = f"{output_html.stem}-assets/fonts"
    return css.replace("__FONT_DIR__", relative_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article_json", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument("--style", choices=sorted(STYLES),
                        help="Override the article JSON style (default: editorial)")
    parser.add_argument("--font-mode", choices=["bundle", "embed"], default="bundle",
                        help="Copy fonts beside the HTML (default), or embed them as data URIs")
    args = parser.parse_args()
    data = json.loads(args.article_json.read_text(encoding="utf-8"))
    validate_article(data)
    language = data.get("language", "en")
    style = normalize_style(args.style or data.get("style", "editorial"))
    if style not in STYLES:
        raise ValueError(f"Unknown article style: {style}")
    articles = {language: data}
    for code, translation in data.get("translations", {}).items():
        if translation.get("title") and translation.get("chapters"):
            articles[code] = translation
    views = "\n".join(render_view(article, code, style) for code, article in articles.items())
    css = (ROOT / "assets" / "article.css").read_text(encoding="utf-8")
    variant_css = ""
    if style != "editorial":
        variant_css = (ROOT / "assets" / f"{style}.css").read_text(encoding="utf-8")
    combined_css = prepare_fonts(css + "\n" + variant_css, args.output_html, style, args.font_mode)
    js = (ROOT / "assets" / "article.js").read_text(encoding="utf-8")
    options = "".join(f'<option value="{esc(code)}">{esc(code)}</option>' for code in articles)
    disabled = "" if len(articles) > 1 else " disabled title=\"No complete translation supplied\""
    title = esc(data["title"])
    document = f'''<!doctype html>
<html lang="{esc(language)}" data-style="{esc(style)}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script>try{{document.documentElement.dataset.theme=localStorage.getItem('editorial-theme')||'light'}}catch(e){{}}</script>
<style>{combined_css}</style>
</head>
<body data-language="{esc(language)}">
<header class="topbar"><div class="topbar-actions">
<select id="language" aria-label="Article language"{disabled}>{options}</select>
<button type="button" id="theme" aria-label="Toggle dark mode">☾</button>
<span class="topbar-divider" aria-hidden="true"></span>
<button type="button" id="font-down" aria-label="Decrease article text size">A−</button>
<button type="button" id="font-up" aria-label="Increase article text size">A+</button>
<span class="topbar-divider" aria-hidden="true"></span>
<button type="button" id="edit" class="edit-icon" aria-label="Edit article text" aria-pressed="false" title="Edit text">
<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4l11-11-4-4L4 16v4Zm12.2-16.2 4 4 1.1-1.1a1.4 1.4 0 0 0 0-2l-2-2a1.4 1.4 0 0 0-2 0l-1.1 1.1Z"/></svg>
</button>
<span id="edit-actions" class="edit-actions" hidden>
<button type="button" id="edit-save" class="edit-action edit-save">Save</button>
<button type="button" id="edit-cancel" class="edit-action">Cancel</button>
</span>
<span id="edit-status" class="edit-status" role="status" aria-live="polite"></span>
</div></header>
{views}
<script>{js}</script>
</body></html>'''
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(document, encoding="utf-8")
    print(args.output_html.resolve())


if __name__ == "__main__":
    main()
