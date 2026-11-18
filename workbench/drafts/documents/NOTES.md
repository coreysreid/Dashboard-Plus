# Important documents: promotion notes

Rechecked **18 November 2026** against the shipped Stock place contract, [DESIGN sections 5 and 6](../../../docs/DESIGN.md), and decisions [0054](../../../docs/decisions/0054-home-layout-uses-the-places-you-already-have.md), 0055 and 0059. This module is a pointer to papers and their household-chosen review dates, **not a document vault**. It stores no copy, number, password or attachment. A name and a broad shared Place are enough. Follow each issuer's current advice for actual renewals; this draft makes no legal-validity or country-specific interval claim.

## Ready for Lane A's promotion pass

- `requires = ["stock"]`; `documents.place` links `stock.places` with `on_delete = "restrict"`. The normal form/list renderer can show a full nested path. The unreleased draft migration is regenerated with a foreign key and place index. Do not try to migrate an old text-place value into a guessed place; no released Documents records exist yet.
- `holder` and `notes` are sensitive. They are absent from the list and the document review sheet. The record's **name**, kind and due date are still ordinary visible data: choose generic titles. The missing-place question uses `{name}`, so it must never become a private detail or document number. The sheet itself is a reminder list, not a private paper copy, and still prints those ordinary titles.
- The six example rows use real `stock.places` names from the shipped Smith, Garcia and Taylor examples: Smith **Front hall**, Garcia **Hall closet** and **Main bedroom**, Taylor **Hall cupboard**. These are invented sample records, not directions to a real person's papers.
- `renew_by` is optional. The household types a date from its own paper or chooses a reminder. Needs attention says **due** 30 days before a date that was entered; no date means no guessed reminder. The draft sheet omits storage place, holder and private notes.

## Core needs and limits

The current private-column guard hides `holder` and `notes` until Show, but it cannot make an entire document row or its ordinary name private. If Lane A wants a fully hidden document, core needs record-level privacy and a print policy before such a title can be entered. Current audit/history and backups retain earlier private values; a permanent erase flow is batch 12 item 45. The draft has no attachment field because private file storage, backup/export and restore behavior need a separate design. See [acceptance checks](ACCEPTANCE.md) before promotion.
