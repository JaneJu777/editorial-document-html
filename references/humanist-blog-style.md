# Humanist blog article style

This is an original warm long-form reading system built from general editorial principles: restrained typography, a calm reading measure, soft chapter fields, and clear supporting components. It does not reproduce or imply affiliation with any third-party publication, AI company, or product.

## Visual decisions

- Warm paper `#faf9f5`, near-black ink `#141413`, muted text `#5e5d59`, restrained hairlines, and a terracotta accent `#c66b4e` create a calm humanist palette.
- Display and chapter headings use the open-source Newsreader family with Noto Serif SC and Georgia fallbacks. Body and utility text use Inter with Noto Sans SC and system fallbacks.
- The hero uses a generous two-column editorial header: title hierarchy on the left and compact metadata on the right. It collapses to one column on narrower screens.
- The main reading measure is `640px`, a comfortable long-form text column. Tables remain horizontally scrollable and may exceed the reading measure only inside their own scroll region.
- Chapter numbers are large muted numerals (`76px`, regular weight `400`, black at `30%` alpha) sitting inside the colored chapter band, set in Newsreader with the Noto Serif SC fallback so the numeral and the hero title share one voice; the chapter title itself stays in the sans stack. Because the colour is an alpha rather than a fixed grey, the numeral harmonises with each band tint instead of being one flat `#999999`. In dark mode the numeral switches to a light low-emphasis grey (`#8b877d`), since 30% black would disappear on a dark band. Subsections remain vertically stacked for steady long-form reading.
- Cards use warm-paper surfaces, thin neutral borders, and modest radii. A plain card and a flow step share one box — hairline border, `12px` radius, `20px` padding — and both centre their content vertically, so a card stretched by a taller neighbour in the same row still shows equal space above and below its text. Do not reintroduce a fixed `min-height`; it pushes the text to the top and makes the bottom gap look larger. Tables use a near-black header with warm-white labels. Quotes use a pale terracotta field and code uses a dark ink surface.
- The card family uses a restrained shared system: 12–14px radii, 20–28px padding, near-black `#141413` deep panels, neutral `#f1efe8` and terracotta-tinted `#f3e3dc` surfaces, an `#d97757`/`#c66b4e` accent, uppercase 11–12px labels, and hairline `currentColor 18%` rules.
- Existing language, theme, text-size, table, flow, TOC, and accessibility behavior is preserved.

## Card family

| Block | Purpose | Notes |
| --- | --- | --- |
| `cards` + `tone` | Short parallel items | Without a tone a card is the plain box below: hairline border on the paper, `12px` radius, `20px` padding, `18px/600` title. With a `tone` — `surface`, `tint`, `ink`, or `accent` — the border is dropped: the fill separates the card from the paper, as in the reference. `accent` is the solid accent field with white text in light mode (`4.2:1`) and near-black text in dark mode, where white on the lighter `#df8b6c` would fall to about `2:1`. Each card may carry an 11px uppercase `label`. A card `icon` is never rendered here — emoji card titles are an `editorial` convention. |
| `compare` | Two or three side-by-side positions | Column `tone`: `old` (neutral surface) and `new` (tinted surface, accent label) mirror the reference's Traditional / AI-native pairs. |
| `keyvalue` | Label/value inventory | Rendered as a definition list with a `150px` label column and hairline rows. |
| `aside` | Secondary material beside the argument | Deep `#141413` panel with a 170px label/title column; `layout: "stacked"` for a full-width variant. |
| `callout` | One emphasis card | `neutral` (soft surface) or `ink` (deep panel). At most one callout per two sections; the tone is the only thing that sets its weight, so do not stack them. |
| `links` | Grouped destinations | 2-column bordered link cards with the path in monospace. |

In dark mode the paper, panels, surfaces, and accent soften rather than invert: deep panels darken to `#121110` and gain a hairline so they still read as a deliberate surface — that hairline on `tone-ink` is the only border left on a tone card — and the solid accent field switches from white text to near-black. The chapter bands are tokenised too — the light pastels become deep tinted panels (`#27333d` blue, `#302c3d` lilac, `#402f28` peach, `#22302b` sage, `#2a3020` olive, `#302c24` sand) with light band ink, so the band text never sits on a bright field. Code blocks keep their dark-ink surface in both themes instead of inverting to a bright block. All card groups collapse to a single column at 700px, and they keep their backgrounds when printed.

The key-value list has no column gap: the label and the value are one continuous line, separated only by the label's weight and opacity. Do not reintroduce a gutter there.

### Vertical rhythm inside a card

Three rules keep the ink the same distance from the top and the bottom edge; all three were verified by measuring painted pixels, not by eye.

1. Prose margins stop at the card edge. `.article-content p` is declared after the last-child resets, so it wins on source order and would otherwise leave a phantom 24px under the final line of a band or a card. One `:is(...) :is(p, ul, ol):last-child { margin-bottom: 0 }` rule scoped to the card containers holds the line.
2. Every card container has equal vertical padding — band `36px`, plain card and flow step `20px`, compare card `20px`, callout `24px`, aside `26px`, link card `12px` — even though the reference ships `36px 36px 38px` and `20px 20px 22px`. Our CJK leading already biases the ink downwards, so the extra bottom padding double-counts it.
3. The half-leading under the final line still reads as padding, so the last line of the band, the compare card, the plain card, the callout, the aside body, the link card, and the flow copy carries a `-.15em` bottom margin. That rule must stay last in the stylesheet: it has to beat the margin resets above it.

Measured ink-to-edge gaps after the fix (light theme, 1440px): band `37/37`, compare card `22/24`, plain card `23/24`, aside `29/32`, ink callout `26/27`. Before the fix the band was `37/65` and the compare card `22/51`. At 390px the band stacks to one column and lands on `26/29`; the extra pixel there comes from the numeral, so `.chapter-number` keeps `line-height: 1` — anything below `1` lets the glyph ink spill above its line box and eats into the top gap.

Do not fabricate third-party logos, custom brand icons, site navigation, author profiles, newsletters, or product calls to action. A callout carries a text label, body copy, and at most one action link — no icons or badges.

## Content fit

Use `humanist-blog` for playbooks, technical explainers, operating guides, research narratives, and long documents that benefit from a calm reading column plus clearly structured supporting components.
## Selection

Set `"style": "humanist-blog"` in the article JSON or pass `--style humanist-blog` to the renderer. Style selection changes presentation only and must not rewrite source content to resemble the reference article.
