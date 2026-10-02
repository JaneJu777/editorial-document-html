# Automatic structure inference

Use `scripts/infer_article.py` before manually authoring article JSON. The goal is not to maximize the number of components; it is to recover the strongest structure already implied by the source while preserving every word.

## Evidence order

1. Explicit source semantics: Markdown syntax, Word paragraph styles, numbering and inline runs, table cells, blockquotes, code fences, links, and images.
2. Repeated structural patterns: isolated short lines, consistent numbered items, consistent columns, or consecutive label/value pairs.
3. Lexical context: process-oriented headings, operational labels, conclusion/warning lead-ins, and note/background lead-ins.
4. Fallback: ordinary paragraph or list.

Never use typography alone as proof when the source structure contradicts it. Never infer a quotation, factual status, warning, comparison, or process that the words do not support.

## Decisions

| Source evidence | Component | Required evidence | Fallback |
| --- | --- | --- | --- |
| H1 or first isolated title-like line | Article title | Short, non-sentence line; explicit H1 wins | Filename |
| Highest remaining heading level | Chapter | Explicit heading or high heading score | Neutral generated `正文` container |
| Next heading level | Section | Explicit hierarchy | In-content heading |
| Ordered items below 流程/步骤/阶段/process/workflow heading | `flow` | At least two ordered items plus process context | Ordered `list` |
| Repeated short `label: value` rows | `keyvalue` | Most labels describe properties, conditions, owners, status, inputs, outputs, or acceptance | `cards` or paragraph |
| 2–5 parallel short labels with explanatory bodies | `cards` | Consistent pair structure; labels are not mainly operational fields | Paragraph |
| 2–3 alternatives below 比较/对比/差异/versus heading | `compare` | Parallel label/value structure plus comparison context | `cards` or paragraph |
| Consistent rows and columns | `table` | Same column count; explicit Markdown/Word table wins | Paragraphs |
| 结论/重点/注意/建议/警告 lead-in | `callout` | Lead-in occurs at paragraph start | Paragraph |
| 补充/说明/备注/背景/旁注 lead-in | `aside` | Lead-in occurs at paragraph start | Paragraph |
| Multiple standalone URLs | `links` | At least two destination lines | Paragraph with links |
| Explicit blockquote syntax | `quote` | Explicit `>` or Word quotation structure | Paragraph |
| Fenced code | `code` | Explicit fence; language is preserved when supplied | Paragraph/preformatted text |

Nested Markdown and Word lists remain nested lists. Even under a process heading, a nested list is not flattened or promoted to a `flow`, because the child hierarchy carries meaning. DOCX bold runs, hyperlinks, and inline image position are preserved when represented as standard OOXML relationships.

Known categorical table values (`高`, `中高`, `中`, `低`, `P0`, `P1`, `P2`, and their English equivalents) become typed chips automatically outside the first column. Unknown values remain ordinary table text; the mapper never guesses a color category from arbitrary prose.

## Confidence

- `0.90–1.00`: explicit source structure or a strong compound rule. Normally accept.
- `0.75–0.89`: repeated structure plus supporting vocabulary. Review quickly.
- Below `0.75`: generated container or ambiguous interpretation. Inspect before delivery.

The generated top-level `mapping_report` records `source`, `component`, `confidence`, and `reason`. It is diagnostic metadata and is not rendered into the article.

## Unmarked source behavior

Unmarked text is not treated as structure merely because a line is short. A heading candidate must also lack sentence-ending punctuation, be isolated by paragraph boundaries, and preferably contain numbering or few words. Sentence-like copy stays a paragraph.

If the document contains no reliable chapter heading, the mapper creates one neutral `正文` container and reports confidence `0.5`. This is a presentation wrapper, not a claim about the source.

## Review boundary

Automatic mapping is deterministic and explainable, but semantic ambiguity remains possible. Correct a low-confidence mapping in article JSON; do not ask the source author to rewrite or annotate the original document unless the underlying meaning truly cannot be determined.
