# Home care promotion acceptance checks

Use temporary fictional Smith, Garcia and Taylor data. Shipped contracts and example places checked **18 November 2026**.

1. **Load:** The draft loads with Stock enabled and its regenerated unreleased 0001 migration matches `tables.toml`. Without Stock, the module stays off with a dependency message.
2. **Place path:** A job linked to `stock.places` **Kitchen › Pantry › Shelf 3** shows that path on its form, list and Home care sheet. Searching by Pantry finds the place; moving it updates the displayed path without changing the job link ID.
3. **Place deletion:** Refuse removal of a place while a current Home care job points to it. Moving or removing the job lets the normal place operation proceed; restoring a job keeps its original place link if that place still exists.
4. **No duplicate alarms:** Shipped `home_layout.equipment` owns alarm test and next-check dates. Home care has no `smoke_alarm` choice or copied alarm examples. One alarm check creates one current reminder, not two.
5. **Record work:** Add Work done to a job with **Done on** and a private **What was done** note. This adds history but does not silently change the job's **Last done** or **Next due**.
6. **Enter next date:** Open the job after the history entry. Type Last done and a Next due date chosen by the household. The form says the history note does not update that date; a blank Next due creates no automatic interval.
7. **Dates shown:** AU/UK/NZ `20/05/27` and US `05/20/27` represent the same day and display in the household's order. A wrong-order date gets the current format example. An impossible date is refused. Work history and current job dates remain distinct.
8. **Due question:** Within 30 days of a person-entered Next due, Needs attention says **due** for that job. A blank date shows no guessed due question; changing the date updates the reminder.
9. **Privacy:** Job notes and Work done `done_by`/notes are absent from initial list/form HTML, Home, Needs attention, picker suggestions and the sheet. Only explicit Show reveals a requested saved field. A private field never names a record or appears in a gap question or unit.
10. **Print:** **Home care reminders** prints ordinary job name, kind, full place, Last done and Next due only. It omits work history and private fields; the household checks ordinary names before sharing.
11. **Three examples:** Smith's gutter-inspection job links **Backyard**; Garcia's bathroom-sealant job links **Bathroom**; Taylor's bike-shed-door job links **Outside › Bike shed**. All places exist in their shipped example TOMLs. Each has one matching Work done row and invented dates.
12. **Delete/restore:** Soft-deleting a job removes its current due question and sheet row. Its Work done history follows the declared cascade/restore behavior, and restoring does not create another completion or calculate a next date. Audit and backups retain older private values.

These are Lane A promotion checks, not a claim that a Home care module has shipped. Sources: `modules/stock/`, `modules/home_layout/`, the shipped renderer and decisions 0054/0055/0059, checked 18 November 2026.
