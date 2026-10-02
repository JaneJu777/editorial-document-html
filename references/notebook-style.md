# Notebook article style

This is an original text-first notebook system built around the Playwrite handwriting family. It uses a general notebook grammar — ruled paper, a margin rule, one pen colour, and pasted notes — without borrowing a third-party masthead, site identity, navigation, illustrations, image treatment, or promotional blocks.

## Visual decisions

- **Ruled paper.** The page is `#fdfdfd` with a `#f6f6f6` hairline every `32px`, drawn with a `repeating-linear-gradient` rather than an image, so the sheet stays self-contained. The interval is scaled by `--font-scale` so the ruling keeps step with the A−/A+ reading-size control. **Keep the rule nearly invisible** — the reference's own `#cccccc` is a visible line under 17px handwriting and competes with the text. Dark mode uses `#171d2a` against the `#121722` paper.
- **One pen colour.** Cobalt `#0044cc` is the ink for body copy, headings, links, rules and numerals — as in the theme, where every element is the same blue. It measures `10.3:1` on the paper. A lighter blue `#3f63b8` carries metadata. Nothing else introduces a second category colour.
- **Margin rule.** A single `1px` pink `#ff80bf` line runs down the left of the reading column, and the text column is indented `34px` past it. Pink is the theme's only other palette colour and it is used exactly the way the theme uses it: as the notebook margin, never as body text. It is never used for small text — `#ff80bf` on the paper is only `1.9:1`.
- **Highlighter.** Pink is the emphasis fill, in two steps: `#ffe3f1` for a swipe inside the page (a `tint` card, the table header, the chapter numeral, a flow step number, a `p0`/`high` chip, **every bold word**) and `#ffd6e9` for whole objects stuck on the sheet (the summary block, a neutral callout). Bold copy carries a `#ffe3f1` swipe behind it, `box-decoration-break: clone` so it hugs the words; on a solid cobalt or vermilion fill the swipe stays off, since it cannot read there. Neither pink is ever a text colour; `#ff80bf` on the paper is only `1.9:1`.
- **Sticky notes come in three fills.** Pink `#ffd6e9` for the summary, neutral callout and positive comparison; yellow `#fff3c4` for link cards and the contrasting comparison; cobalt for the ink callout. Each note uses an irregular polygon edge with small alternating tears on all four sides, then tilts a fraction of a degree (`±.35–.5deg`, alternating where a group repeats), so it reads as torn and pasted rather than typeset. The `Generated summary` label becomes a small paper tag on the pink note, never a second pink chip on a pink note.
- **Teacher's pen.** `#b30000` is the vermilion accent, taken from the theme's alternate style variation; it is the `accent` card fill with near-white text (`14.1:1`).
- **One handwriting system at every size.** Every Latin glyph uses Playwrite US Modern, with Playwrite US Trad for the italic voice; every CJK glyph uses LXGW WenKai. The same ordered stack is used for hero titles, body copy, metadata, tables, chips, controls and code — there is no remaining Inter or Ma Shan Zheng path inside the notebook theme. Body copy is `17px` at `line-height: 1.84`, the theme's own measure.
- **Square, rough, filled.** Cards and buttons stay square-cornered; table frames, internal table rows, key-value dividers, and quote markers reuse the same two-pass rough pen stroke as the workflow. The top bar keeps its `2px dotted` cobalt rule. Nothing takes a shadow. The circles are deliberate: the flow step number sits on a pink dot and the quote/step marks read as a hand-drawn ①.
- **Boxes are opaque, margin notes are not.** Anything that reads as an object on the sheet — card, comparison panel, callout, flow step, link card, key-value list, table, code block — carries the paper fill, so the page's ruling stops at its edge and never doubles as an inner divider. The blocks whose marker *is* the pink margin rule (`summary`, `aside`, `blockquote`) stay on the ruled sheet: they are writing in the margin, not an object pasted onto it. The blockquote marker uses the same double-pass vertical pen mask as the workflow frame rather than a straight CSS border.
- **The rule after a chapter title is drawn twice.** `h2::after` is a 12px band masked by two slightly different bezier strokes, echoing the double-pass roughness of an Excalidraw line rather than a decorative wave. The same mask system draws the flow frame (four strips, one per edge, on a single `::before`) and its loose double-stroke arrow. Both passes recolour with the theme and keep rounded pen ends; do not replace them with a printed border or typeset `↓`.
- **Card titles stay plain.** The torn sticky-note paper already carries the visual emphasis, so card headings have no separate pink swipe. Their spacing still moves to the body below (`h4 + :is(p, ul, ol, dl, div) { margin-top: 12px }`).
- **Reading measure.** The column is `780px` (about 43 CJK characters), narrower than the other styles, matching the theme's `640px` content width intent rather than an editorial spread.

## Component mapping

| Block | Treatment |
| --- | --- |
| `cards` | Torn yellow sticky note, alternating two edge shapes and a slight rotation; the title stays transparent without a separate highlighter swipe. `surface` = paper, `tint` = pink highlighter fill, `ink` = solid cobalt panel, `accent` = solid vermilion — all retain the torn-note silhouette. Card emoji are not rendered — that is an `editorial` convention. |
| `compare` | Two torn notes with opposing slight rotations: `old` uses yellow paper, `new` / `accent` use pink paper. |
| `keyvalue` | Two-pass rough row dividers on the paper fill with `16px` side padding so the fill reads as a panel, uppercase labels, no column gutter. |
| `aside` | Always stacked, never two-column: no left rule; label/title/meta on top, closed by a pink double-pass rough stroke, then the body. No fill — the page ruling runs behind it. |
| `callout` | A sticky note: pink fill for the neutral tone, cobalt for `ink`, both tilted. The one action button is a solid pen-filled square with tracked caps, matching the theme's button. |
| `links` | One yellow sticky note per destination: fill, tilt, underlined title that clears on hover. No border and no pink edge — the note itself is the emphasis. |
| Table | Two-pass rough cobalt frame on the paper fill, highlighter header, two-pass hand-drawn internal row rules and no vertical rules. Chips use distinct semantic fills: green for high, yellow for medium-high / P1, blue for medium / P2, pink for P0 and gray for low / later. |
| `flow` | Steps framed by two slightly offset rough strokes on all four sides, joined by a loose double-stroke arrow, each step numbered on a pink dot. |
| Lists | A handwritten dash for unordered items, cobalt tabular numerals for ordered items. |
| Quotes | Pink double-pass hand-drawn left rule, no fill, in the italic handwriting face. |
| Summary | The whole block is a pink sticky note, tilted; `Generated summary` is a small paper tag on it. |
| Bold copy | A pink swipe behind the words, in every component; off on solid cobalt or vermilion fills. |

## Dark mode

Dark is "the same sheet under a desk lamp", not an inversion of the palette: paper `#121722`, ruling `#171d2a`, chalk-blue ink `#d7e3ff`, a plum highlighter `#3a2740`, a plum sticky note `#4a2c40`, a muted mustard note `#3e3a22`, and the margin rule softened to `#e078ad`. As in `newsroom` and `humanist-blog`, the solid cobalt panel inverts to a light chalk panel with dark text, since a dark fill on a dark page would not read as a surface. Ruled lines are switched off in print, along with the margin rule, top bar and TOC.

## Boundaries

Use `notebook` for reflective, personal, or teaching-oriented documents — notes, walkthroughs, handbooks, working docs — where a handwritten voice is an asset. Do not use it for content that must read as formal or corporate. Do not add the theme's doodle illustrations, its masthead, its social row, or fabricated imagery; and do not turn the margin rule or highlighter into arbitrary decoration.

## Selection

Set `"style": "notebook"` in the article JSON or pass `--style notebook` to the renderer. Style selection changes presentation only and must not rewrite source content to resemble the reference theme.
