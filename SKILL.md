---
name: editorial-document-html
description: Convert Markdown, Word (.docx), or plain text into a source-faithful standalone HTML article in editorial, newsroom, humanist-blog, or handwriting-notebook style. Use when source structure or component types must be inferred from the writing itself, including unlabelled headings, lists, comparisons, key-value information, tables, notes, quotes, and processes; do not use for ordinary proofreading or unrelated websites.
metadata:
  version: 2.1.0
  short-description: Infer document structure and render a styled HTML article
---

# Editorial document to HTML

Turn a source document into a portable, reviewable article without requiring the author to label UI components. Preserve wording and provenance; infer presentation from document structure and meaning. The four presentation styles share one semantic article schema:

- `editorial`: spacious product-planning article.
- `newsroom`: cream-paper broadsheet.
- `humanist-blog`: warm humanist long-form article.
- `notebook`: ruled-paper handwriting system with torn notes and rough pen strokes.

Do not copy site branding, navigation, proprietary assets, promotional modules, or source text from a visual reference. This skill does not read from or write to the portfolio project.

`humanist-blog` is the public name for the warm long-form style. The renderer accepts the former `claude-blog` identifier only as a deprecated compatibility alias and always emits `data-style="humanist-blog"`. Do not use the legacy name in user-facing copy, examples, filenames, or new article JSON.

## Default workflow

1. Inspect the source and preserve its wording, links, media, table data, ordering, and metadata. Never invent an author, date, translation, claim, quotation, or missing section.
2. Run automatic semantic inference first:

   ```bash
   python3 scripts/infer_article.py source.md article.json --style notebook
   ```

   It accepts `.md`, `.markdown`, `.txt`, and `.docx`. It recognizes explicit markup when present and uses conservative structural and lexical evidence when it is absent. Read [references/inference-rules.md](references/inference-rules.md) when mapping behavior matters.
3. Review `mapping_report` in the generated JSON. Accept high-confidence structural decisions; inspect low-confidence decisions. Ambiguous material must remain an ordinary paragraph or list rather than being promoted to a decorative component. The user should not need to add component names or style labels.
4. Validate before rendering:

   ```bash
   python3 scripts/validate_article.py article.json
   python3 scripts/render_article.py article.json article.html
   ```

   Read [references/article-schema.md](references/article-schema.md) only when manually correcting the semantic JSON or extending a component. The machine schema is [references/article.schema.json](references/article.schema.json).
5. Read only the selected style reference before making visual decisions: [editorial defaults](references/article-schema.md), [newsroom](references/newsroom-style.md), [humanist-blog](references/humanist-blog-style.md), or [notebook](references/notebook-style.md).
6. Check source completeness, desktop and narrow widths, light/dark themes, A−/A+ bounds, hash navigation, table scrolling, sticky table headings/first column, links, alt text, and print behavior. Run the deterministic suite:

   ```bash
   python3 scripts/check_skill.py
   ```

   The repository preview gallery uses one dedicated fixture per style so the sample's voice and component mix fit the selected theme. Rebuild all four after changing renderer or theme behavior:

   ```bash
   python3 scripts/build_previews.py
   ```

Rendered HTML includes an Edit button for local text-only corrections. Save persists text overrides in that browser's `localStorage`; Cancel restores the text present when editing began. Editing never rewrites the source Markdown/DOCX, article JSON, links, component types, or CSS. Regenerating or opening the file at a different path does not carry those local overrides with it.

Do not publish or overwrite the source document unless asked.

## Inference boundaries

- Explicit structure wins: Markdown/Word headings, real lists, tables, blockquotes, code fences, links, and images are retained.
- Unlabelled short lines may become headings only when length, punctuation, isolation, and numbering agree. Sentence-like text stays prose.
- An ordered list becomes a `flow` only under a process-oriented heading. Otherwise it remains a list.
- Consecutive `label: value` lines become `keyvalue` for operational/property labels, or `cards` for 2–5 parallel concepts with explanatory bodies.
- Conclusion/warning lead-ins may become `callout`; note/background lead-ins may become `aside`.
- Consistent rows and columns become a semantic table. Do not turn prose alignment into a table.
- Components are inferred from source meaning, never added to make the page look richer. See [references/inference-rules.md](references/inference-rules.md) for confidence thresholds and fallbacks.

## Editorial constraints

- Map genuine hierarchy to title, chapters, sections, and small headings. Do not promote bold lead-ins into chapters.
- Preserve paragraph boundaries and nested list order. Soft line wraps remain spaces.
- Apply bold only where the source emphasized a label or claim; never add emphasis decoratively.
- Use cards for short parallel concepts, tables for row/column comparisons, and flow only for an ordered process or lifecycle.
- Add chips only to categorical values with a declared mapping.
- A generated summary must be source-faithful and labelled generated. A translation must be complete and must never be silently machine-generated.
- `editorial` card titles use a meaningful emoji selected from the card title and body when no explicit `icon` is supplied. Quiet styles omit card emoji.

## Portability and maintenance

The renderer defaults to a portable bundle: the HTML references version-pinned, locally packaged open-source fonts copied into `<output-stem>-assets/fonts/`. Use `--font-mode embed` for one large self-contained HTML file. Keep images beside the output with relative paths.

After modifying the project skill, synchronize and verify the installed copy:

```bash
python3 scripts/sync_installed_skill.py ~/.codex/skills/editorial-document-html
python3 scripts/check_skill.py --installed ~/.codex/skills/editorial-document-html
```

Keep the project `SKILL.md`, style references, CSS, schema, examples, tests, and installed copy consistent. Do not use floating font URLs or unversioned external assets.
