# Article JSON shape

Use UTF-8 JSON. The renderer accepts one article plus optional complete translated articles. Omit unknown metadata; do not use placeholders that look like facts.

For ordinary use, generate this structure automatically with `python3 scripts/infer_article.py source.md article.json --style <style>`. Manual component annotations are not required. The generated `mapping_report` explains the structural and semantic evidence used for each mapping; review low-confidence decisions and leave ambiguous material as prose. Validate the result with `scripts/validate_article.py`. The machine-readable companion schema is `references/article.schema.json`.

```json
{
  "style": "editorial",
  "language": "zh-CN",
  "title": "示例标题",
  "eyebrow": "产品规划",
  "created_at": "2026-09-24",
  "author": "Jane Ju",
  "summary": "一句源于文档的摘要。",
  "summary_generated": false,
  "chapters": [
    {
      "title": "决策摘要",
      "summary": "可选的章节摘要；humanist-blog 风格会将它放在彩色章节标题块中。",
      "blocks": [{"type": "paragraph", "content": "章节开头。"}],
      "sections": [
        {
          "title": "产品机会",
          "blocks": [
            {"type": "paragraph", "content": ["普通文字，", {"text": "关键结论", "bold": true}, "继续正文。"]},
            {"type": "list", "ordered": false, "items": ["并列点一", "并列点二"]},
            {"type": "heading", "text": "小小标题"},
            {"type": "cards", "items": [
              {"title": "概念 A", "blocks": [{"type": "paragraph", "content": "简短说明。"}]},
              {"title": "概念 B", "blocks": [{"type": "list", "items": ["要点一", "要点二"]}]}
            ]},
            {"type": "table", "label": "场景优先级", "headers": ["场景", "价值", "优先级"], "first_column_header": true,
             "rows": [["场景 A", {"text": "高", "chip": "high"}, {"text": "P0", "chip": "p0"}]]},
            {"type": "flow", "label": "审查流程", "steps": [{"title": "数据更新", "note": "增量同步"}, {"title": "人工判断"}], "loop": "重新评估"}
          ]
        }
      ]
    }
  ],
  "translations": {
    "en": {"language": "en", "title": "Example title", "chapters": []}
  }
}
```

## Block rules

- `paragraph`: `content` is a string or an array of plain strings and `{text, bold?, href?}` runs. A single bold sentence maximum per paragraph. A source link should use an `href` run rather than raw HTML.
- `list`: `ordered` defaults to false. Items are strings, inline-run arrays, or `{content, children, ordered?}` for nested lists. `editorial` marks unordered items with `✦` and ordered items with teal bold numerals; `notebook` uses a handwritten dash; `humanist-blog` and `newsroom` keep their own round markers, so the same JSON reads correctly in every style.
- `heading`: small in-content heading (`h4`); use chapter/section objects for higher levels.
- `cards`: 2–5 short, parallel items. Each item has `title`, optional `label` (uppercase micro label above the title), optional `tone`, and a `blocks` body (or a single `content` run). In `editorial`, the renderer chooses a meaningful title emoji from the card's title and body when `icon` is omitted; an explicit `icon` overrides that choice. `humanist-blog`, `newsroom`, and `notebook` hide card icons. Headings never take one. Tones: `surface` (neutral paper), `tint` (light accent), `ink` (deep panel), `accent` (solid accent). Omitting `tone` keeps the style's default treatment. Each style resolves the tones in its own palette — `editorial` uses its soft block, cool tint, ink panel, and deep teal; `humanist-blog` uses its warm surfaces and terracotta; `notebook` uses a highlighter tint, a solid pen panel, and a teacher's-pen red. Never carry one style's tone colours into another; check the rendered style instead of assuming a tone looks the same everywhere.
- `compare`: 2–3 side-by-side columns for a direct contrast. Each column has `label`, optional `tone` (`old`, `new`, `neutral`, `accent`), and either `content` or `blocks`. Use `label` on the block for an accessible group name. Do not use it for long sections.
- `keyvalue`: `rows` of `{label, content?|blocks?}` rendered as a definition list whose label and value columns sit flush against each other with no gutter. Use for prerequisites, infrastructure, metrics, or any short label/value inventory. Keep labels to a few words.
- `aside`: a supporting panel that sits outside the main argument — `{label?, title?, meta?, blocks, layout?}`. `layout: "stacked"` drops the two-column head. Reserve it for genuinely secondary material; it is not a general paragraph container.
- `callout`: one emphasis card. `tone` is `neutral` (default, soft surface) or `ink` (deep panel). Optional `action: {label, href}` adds one link out. No icons or badges; keep it to at most one callout per two sections.
- `links`: `items` of `{title, href?, note?}` rendered as link cards. Use only for genuine destinations; `note` carries the path or a short qualifier, not a sentence.
- `table`: `headers` and `rows` must have the same column count. Set `first_column_header` when the first cell identifies each row; this creates sticky row headers and a sticky first header cell. A cell is a string, inline-run array, or `{text, chip}`. Supported chip tones: `high`, `medium-high`, `medium`, `low`, `p0`, `p1`, `p2`, `later`. Use only for categorical values such as priority or assessed level.
- `flow`: `steps` are ordered `{title, note?}` objects; `loop` is optional text for a feedback cycle.
- `image`: `{src, alt, caption?}`. Keep `src` relative to the generated HTML when possible.
- `quote`: `{content, cite?}`. `code`: `{text, language?}`.

The renderer numbers chapters and sections automatically (`01`, `1.1`, `1.2`, …); do not put those numbers in titles. A chapter may include an optional `summary`: in `humanist-blog` it sits inside the colored chapter band, in `editorial`, `newsroom`, and `notebook` it renders as a lead paragraph directly under the chapter heading. When a chapter has no summary but opens with a paragraph, the `humanist-blog` style promotes that paragraph into the band; the other styles always print it as an ordinary paragraph and never invent a summary. It derives stable anchor IDs from their ordinal positions. A translation must include a complete article, not only UI labels. Without one, the language button remains present but disabled. The content must never be silently machine-translated.

`style` accepts `editorial` (default), `newsroom`, `humanist-blog`, or `notebook`. The CLI flag overrides the JSON choice without changing content, for example `python3 scripts/render_article.py article.json output.html --style humanist-blog`. The deprecated `claude-blog` value remains an input-only compatibility alias and is normalized to `humanist-blog`; never write it into new files. All styles use this same schema, so do not restructure or rewrite source text merely to switch presentation.

Every block above — including the whole card family (`cards` with tones, `compare`, `keyvalue`, `aside`, `callout`, `links`) — renders in all four styles and is reusable for any document. Automatic inference handles the common source patterns described above; ambiguous semantics still fall back to prose. The `examples/` folder contains a dedicated preview fixture for each style so visual QA uses content whose voice and component mix fit the selected theme. `humanist-blog-preview.json` remains the broadest component exercise.

## What the extractor does and does not recover

`scripts/extract_source.py` is an inventory, not an interpretation. Read the original alongside it and never let the extractor decide the structure.

| Source | The extractor returns | Still decided when authoring the JSON |
| --- | --- | --- |
| `.md`, `.markdown` | Headings, lists, links, bold runs, tables, blockquotes, images, fenced code, and paragraphs | Ambiguous semantic promotion such as cards versus key-value rows |
| `.txt` | Paragraph groups plus inferred headings, numbered/bulleted lists, label/value rows, tabular rows, URLs, and prose | Low-confidence heading or component decisions |
| `.docx` | Paragraph styles, numbering format/level, tables, embedded media inventory, core properties (author, created), and unmarked-text inference | Complex floating-image placement, captions, and unusually customized numbering |

## Source → component

The same source shape can legitimately become different components, so this mapping is a judgment, not a lookup. Keep it consistent:

| Source feature | Maps to | Boundary |
| --- | --- | --- |
| Document title (H1, or the filename) | `title` | Use the filename if no title exists; never invent one |
| Top-level section (H2 / `Heading1`) | a chapter | Only promote to a chapter when the document really has that level; a bold lead-in is not a heading |
| Second-level section (H3 / `Heading2`) | a section inside the chapter | |
| Opening paragraph that summarises a chapter | `chapter.summary` | In `humanist-blog` it moves into the band; when absent the first paragraph is used without duplication |
| 3–5 short parallel concepts | `cards` | Long narrative paragraphs are not cards |
| Two or three columns whose headers are positions or options | `compare` | If the rows pair up cell-by-cell, a `table` is the more faithful mapping |
| A real data table (several rows and columns) | `table` | Set `first_column_header` when the first cell identifies the row |
| A short "label: value" list | `keyvalue` | Labels stay a few words |
| Ordered steps, stages, or a lifecycle | `flow` | Only for a genuinely ordered process; a topic list is not a process |
| A paragraph that belongs beside the main line (footnote, caveat, scope) | `aside` | Not a general paragraph container |
| A single emphasis, conclusion, or warning | `callout` | At most one per two sections; add none if the source has no such beat |
| Several URLs with a path or qualifier | `links` | Real destinations only; `note` carries the path, not a sentence |
| A direct quotation | `quote` | |
| Code or configuration | `code` | |
| A figure with a caption | `image` | Keep alt text and caption; prefer a relative `src` |

Anything the source lacks stays absent. Never add a callout, comparison, or aside to make a page look richer — a rendered article that is missing a component is correct; one that invented one is not.
