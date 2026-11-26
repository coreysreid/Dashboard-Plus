"""One short invented example and a plain warning for each list a helper may fill in, used by the helper's guide (decision 0138)."""
from __future__ import annotations

# table name -> (one entry, as a helper sends it; what to watch for). Ids are placeholders for a record read first.
# tests/test_helper_guide_0138.py sends every example through the real checks, so none of them can be out of date.
EXAMPLES: dict[str, tuple[dict, str]] = {
    "pets__weigh_ins": (
        {"pet": 3, "day": "2026-11-20", "weight": 4.2},
        "The weight is in kg, as the field says. Never convert pounds or stones yourself: ask the person."),
    "pet_feeding__servings": (
        {"pet": 3, "given_at": "2026-11-20T07:15", "kind": "bowl", "food": "Dry food", "amount": 60, "unit": "g"},
        "Food put out, not food eaten. Send an amount and its unit together, or neither. Send each real feeding once, "
        "never a day's total as one feeding. Review marks a feeding that looks like one already there."),
    "vehicle_running__readings": (
        {"vehicle": 2, "read_at": "2026-11-20T09:00", "distance": 48500, "unit": "km"},
        "Send the unit the odometer showed (km or mi); it is never converted. Review does not question a reading that "
        "is lower than the last or in another unit when a helper sends it, so read the vehicle's earlier readings "
        "first and ask the person about any that look wrong."),
    "routines__times": (
        {"routine": 5, "outcome": "done", "planned_for": "2026-11-17", "done_on": "2026-11-18"},
        "One past time a routine was done or skipped. It does not move the routine's next date or its last-done "
        "date; the person does that with Mark done. Never guess a date: leave planned_for out if unknown."),
    "routines__routines": (
        {"name": "Check the smoke alarms", "repeat_count": 3, "repeat_unit": "months", "next_due": "2027-02-01"},
        "Send the next date the household told you. Leave last_done out: earlier times go in the Done or skipped list."),
    "garden__jobs": (
        {"title": "Prune the roses", "due_on": "2026-12-05"},
        "To add a job that was already done, send done as true and the day it was done as done_on. If you do not "
        "know the day, leave done_on out; Dashboard never guesses one. Mark done is a button only a person presses."),
    "vehicle_running__estimates": (
        {"service": 4, "kind": "dealer", "quoted_on": "2026-11-02"},
        "Send who quoted it and when. The cost and what the quote includes are private: leave them out and tell the "
        "person which quotes still need them."),
}
