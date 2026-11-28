# A quieter visual language for Dashboard Plus

Batch 24 item 134. Planned **27 November 2026**. This is an original visual direction in words, not shipped icons or a new chart library. The existing green links, warm neutral surfaces and strong text order are a useful base. Keep the household's words and figures primary; pictograms help people find an area, and colour helps scan a state, but neither carries a fact alone.

## What the current images show

| Screenshot | Observation and implication |
|---|---|
| [Smith Home](../../../docs/screenshots/smith/04-home.png) | The many area cards have clear names but nearly identical outlines, density and green links. A small, consistent area pictogram beside each **name** could make scanning easier, especially when a household enables many modules. The icon must not replace the name. |
| [Taylor Things to do calendar](../../../docs/screenshots/taylor/18wa-things-to-do-calendar.png) | Green tab and filter pills compete with the four coloured state chips. Preserve the visible selected-tab fill, but let status shapes and words take priority inside the grid. The legend and day list already explain marks without colour. Leave a blank day unmarked. |
| [Smith feeding calendar at phone width](../../../docs/screenshots/smith/18zbb-feeding-calendar-phone.png) | Calendar cells are necessarily small at 320 px. Keep one short mark and count in the cell, with the full **in words, day by day** list directly after the legend; do not try to fit full event names into cells. |
| [Garcia dose calendar at phone width](../../../docs/screenshots/garcia/18ze-dose-calendar-phone.png) | This generated capture still says **Given to #4**. Decision 0142 changed that to a neutral person label. Use the image only to study cell density and Show placement; refresh it before quoting its words as current. The private count and Show boundary must remain intact. |
| [Garcia first aid list](../../../docs/screenshots/garcia/18b-first-aid.png) | The simple table reads easily, but its area has no distinct visual cue. A kit outline beside the heading can help locate it without changing the table or implying that the kit is ready. |

The screenshot gallery does **not** include a chart page, dark mode, high contrast or print capture. The styling in `src/dashboard/web/templates/base.html` covers those modes, but a visual judgement of charts in those modes needs fresh live captures. Generated screenshots may lag the latest decision; record the source commit and date with each new capture.

## Shapes, type and colour

1. **One restrained family.** Keep the existing system font, strong headings, underlined links and quiet cards. Use a 24 px square grid, a rounded 1.75–2 px stroke and no fill for area pictograms. At phone width keep the pictogram at the start of the area heading; at desktop align it with the heading, not as a large tile. No decorative icon beside every record row.
2. **Separate navigation from state.** The green accent means an action or link. Calendar states keep their current meaning across all lists: ✓ Done, ● Recorded, – Skipped, ○ Due but not recorded as done, ◇ Planned. Maintain the existing solid/dotted/dashed edges and the written legend. Do not recolour a whole card red because a date is due or late; say the date and status in words. A missing entry is blank, not a failure state.
3. **Charts show data before style.** Dots and bars use one main mark colour plus axis text. A current, incomplete bar remains striped; a period with no recorded amount stays a dashed empty outline with its words. Keep the scale, units, source count, readable data table and any fitted-scale warning. A line is only drawn where the chart declaration allows it; never smooth over missing days or make a colour gradient imply improvement. On a phone place title, caveat, chart and table in that reading order.
4. **Light and dark.** Use semantic roles already present (`--bg`, `--card`, `--fg`, `--muted`, `--accent`, `--line` and five calendar-state roles) rather than a separate palette per module. Check body text, muted copy, links, focus marks, marks and cell borders against their **actual** background in both themes. Decorative area icons may use foreground; they do not need eighteen colours.
5. **High contrast and print.** In forced-colours mode, use system colours, visible strokes, patterns and a selected-state border; never depend on custom fill. On paper, use black/white marks and outlines with the same day list and chart table. Hide only live controls, not the evidence or warnings; do not assume a printer preserves backgrounds. A pictogram remains understandable as an outline, or can disappear if its nearby text already names the area.
6. **Focus and motion.** A keyboard focus ring surrounds the whole clickable target; an icon-only button is not introduced. Keep links underlined and Show a deliberate text button. No animated chart entrance, pulsing warning or colour-only hover. Screen readers get the link or heading's text once, not both the visible label and a redundant icon name.

## Original pictograms to draw, if the core adopts them

These are descriptions for a single original outline set, not borrowed assets. Put each beside the **written module name** and mark the SVG decorative (`aria-hidden`) there. If used alone in another context, give the control its full written name. The same symbol must never stand for both a module and a status.

| Shipped module | Original outline idea | Avoid implying |
|---|---|---|
| People | Two simple head-and-shoulder arcs | that only two people can be listed |
| Household stock | A jar outline with a level line | that every item is food or full |
| Home layout | Two connected room rectangles and one doorway gap | a certified floor plan or safe exit |
| Medical readiness | A first aid kit outline with a small plus | that a kit is checked or complete |
| Medicine doses | One capsule outline split at the centre | that a planned dose was given |
| Pets | One paw outline | the species or health of a pet |
| Pet feeding log | A shallow bowl with one short fill line | food eaten instead of food put out |
| Readiness | A question card with one corner folded | an official pass or safety score |
| Routines | A circular arrow ending at a small check | that an unrecorded day was missed |
| Bills and insurance | A page outline with a small due-date corner | that a bill was paid or cover is active |
| Important documents | Two offset paper outlines, no number or seal | that the app stores a document copy or ID |
| Home care | A house roof above a short tool handle | that a job is done or an alarm is safe |
| Vegetable garden | A two-leaf sprout above one soil line | a harvest amount or edible plant |
| Things lent out | A box with a short outward arrow | that an item was returned |
| Utilities and accounts | A plug outline with two prongs | that power is on or an account is verified |
| Vehicle running log | An odometer arc with one needle | a distance-based service prediction |
| Vehicles | A car side outline with two wheels | that every vehicle is a car |
| Wine collection | A bottle outline without a label or brand | quantity, value or recommendation |

This set uses no branded symbols, emergency-service badge or medical safety certification. Prototype it first on Home, where the area names are already visible. If a symbol is ambiguous in a five-second recognition check, change it or omit it rather than adding a legend for navigation.

## Build order and checks

1. **Capture the current UI.** Regenerate the three invented households' screenshots from current main and add live examples of at least one dot chart, bar chart, month calendar and timeline at 320 px and desktop in light, dark, print and forced-colours modes. The current gallery cannot prove those views.
2. **Test tokens without icons.** In the current CSS, measure text, link, form-border, focus, chart-mark and calendar-edge contrast against their real backgrounds. Test the five statuses with greyscale and colour removed. Fix a failed state with text, symbol or border first; use hue only as a second cue.
3. **Prototype the area set.** Draw the eighteen outlines on the same grid, with one stroke system and no external icon font or library. Try them beside Home headings at 320 px, desktop and large text. Keep module names visible and links' accessible names unchanged.
4. **Check charts and calendars.** Use invented records with one point, a missing period, a partial period, two units and a private dose. Compare every mark with the table and day list. Before Show, no private title, icon tooltip, SVG text, print or accessible name reveals a person or medicine. Print charts and calendars in black and white and compare extracted words with the on-screen table.
5. **Release only after a household test.** Ask User 1 to find three areas and explain a planned, due and recorded calendar mark without a colour legend. Watch a keyboard and screen-reader pass, large text, 320 px, dark and high-contrast modes. If icons slow navigation or confuse status, keep text alone.

## Sources and limits

Repository sources checked **27 November 2026**: `src/dashboard/web/templates/base.html` chart/calendar/theme rules, `src/dashboard/core/calendars.py`'s five symbols, `modules/INDEX.md`'s shipped module list, decisions 0109, 0119, 0124 and 0142, and the five named screenshots above. The screenshots are generated illustrations, not proof of current chart, print or dark-mode behavior.

Accessibility guidance checked **27 November 2026**: W3C WCAG 2.2 explanations of [Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) and [Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html). The guidance is a basis for the checks above; this draft does not claim WCAG conformance or provide measured contrast results.
