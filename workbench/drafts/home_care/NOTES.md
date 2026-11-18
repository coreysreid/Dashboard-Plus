# Home care: promotion notes

Rechecked **18 November 2026** against shipped Stock Places, Home layout equipment, [DESIGN sections 5 and 6](../../../docs/DESIGN.md) and decisions 0054, 0055 and 0059. Home care records jobs and a person's chosen dates. It gives no maintenance interval or instructions for roof, gas, electrical or fire work; follow the relevant manual, qualified provider or local authority for an actual job. Example dates are invented and convey no recommended frequency.

## What the draft now uses

- `requires = ["stock"]`; `jobs.place` links `stock.places` with deletion restricted while a job uses it. The unreleased 0001 migration has been regenerated with a place foreign key and index. The three examples refer to actual Smith **Backyard**, Garcia **Bathroom** and Taylor **Bike shed** places.
- Home layout already owns smoke-alarm equipment, its last test and next check. Home care therefore does **not** offer a `smoke_alarm` job kind or duplicate those example checks. A future maintenance job that must link a specific alarm needs a reviewed `home_layout.equipment` link and `requires = ["stock", "home_layout"]`; do not copy the same dates into two records.
- Job `notes`, Work done `done_by` and Work done `notes` are sensitive and absent from lists and the sheet. Job names remain ordinary and printable, so use broad titles and keep codes and personal details out. The missing-place question uses the ordinary `{name}` only.
- **A repeating job is manual today.** After work, add **Work done** with the job and **Done on** date, then open that job and type **Last done** and the next **Next due** date chosen from the manual, provider or household plan. Leaving Next due blank means no inferred reminder. The print sheet is a snapshot of the current job dates.

## Core needs and limits

Saving Work done does not update `jobs.last_done` or `jobs.next_due`. A future one-step **Mark done** needs one atomic change that adds history, updates Last done, and asks for a specific next date. Any proposed automatic repeat must first store the household's chosen rule and anchor date and define what editing, deletion and restoration do. The generic event recurrence does not update a module job. Do not show an automatic schedule until those pieces ship. Private values remain in audit and backups under current core behavior; permanent erase is a separate batch 12 design. See [acceptance checks](ACCEPTANCE.md).
