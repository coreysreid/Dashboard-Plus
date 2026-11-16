# Medical readiness draft — promotion decisions

This module records first aid kits, checks and training renewals. It gives no medical instruction, diagnosis or claim that a household is prepared. Allergies, conditions, medication and care details belong in People's sensitive details. Kit supplies and their minimums and use-by dates belong in Household stock's first-aid category.

## Answers to the previous open questions

- **Specific Stock items or a note for a kit check?** A check record holds the date, checker and a short note about what was found. The household updates missing or expired supplies in Stock. Linking every component to a kit would duplicate Stock and require a new cross-module membership rule; add it only if household testing shows the note and Stock place are insufficient.
- **Generate the next check date?** The household enters `next_check` on the kit, based on its own kit guidance or plan. A new check record is history and does not create a recurring reminder. A due watch on the kit's one current `next_check` avoids old check rows producing stale reminders. The household must update `last_checked` and `next_check` after logging a check. Lane A could later make that a single “Complete check” action that writes the check record and both kit dates atomically; it should not invent an interval.
- **What can print?** The optional “First aid at home” sheet lists kit names and places, last and next checks, and training person/course/provider/renewal. It excludes check notes and private People details. Confirm the sheet before sharing it; a full location path becomes important if Home layout is promoted.

## What the household sees

A new household sees “Add a first aid kit and where to find it.” The kit form asks for a place and optional check dates. *Worth filling in* asks where a recorded kit is kept if the place is blank. The desired question “Is there a first aid kit?” when none is recorded needs an unfiltered `none` gap, which the current core validator rejects; the `empty` first step is the available first-visit wording until Lane A adds that support. *Needs attention* says a kit check is “due” or “overdue”, never “expired”; training renewals use “due” too. Training is optional, because not every household has completed a course. A check can be logged without falsely implying that supplies have been replaced.

## Core integration needed later

- If Home layout replaces Stock places, migrate kit place links along with Stock item links and show full paths in its form, list and sheet. The current sheet prints only the linked Stock place name.
- Accept an empty `none = {}` filter in `watch.gaps` so a module can ask “Is there a first aid kit?” when its kits table has no rows, without adding a fake field or name condition.
- A one-step “Complete check” flow would need an atomic update to the kit's last and next check dates, plus its check history. This is a convenience improvement, not a reason to delay promoting the present manual flow.
- If guidance links are added later, cite recognised first aid and health bodies, check them for the chosen country and record their reuse terms. This draft contains no medical guidance or fixed testing interval.
