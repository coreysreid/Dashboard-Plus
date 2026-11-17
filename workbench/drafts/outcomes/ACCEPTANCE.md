# Outcomes acceptance checks

Checked **2026-11-17**. Use invented records only. All examples assume a local November 2026 viewing date.

1. A new household with no movements, receipts or prompt answers sees baseline invitations, **not** zero waste, zero shortages, zero spend, or “fully ready.”
2. One completed month of waste entries and a partial second month shows the recorded entries for each period, but no comparison claim. After the household confirms two complete months, show the comparison and exact 31/30-day basis.
3. Three `thrown_away` or `expired` movement entries count as three entries even if one is two tins and another is one litre. `used` and `given_away` do not count. Amounts never sum across unlike units.
4. An item that was zero for four days creates one stock-out episode, not four. If it is restocked and runs out again, that is a second. A current zero with no opening stock history cannot establish a past shortage.
5. An inventory correction that crosses zero rebuilds the episode history. The evidence view names the correction and shows that the old month changed.
6. A receipt with two lines, a discount and tax contributes its reviewed total once. A duplicate import contributes nothing extra. A receipt in another currency appears in a separate group.
7. A drop from $438.10 to $412.30 says **“Tracked shopping”** with the two totals and coverage, never **“Saved $25.80.”** An unreviewed receipt prevents a complete comparison.
8. One readiness prompt with a valid matching record still shows unanswered until the person answers it. `not_yet` and confirmed `not_relevant` count as looked at, but only `yes` appears in the Yes count.
9. A new prompt version or changed home applicability stops a direct readiness comparison. A prior answer remains in history and can be reviewed; no old Yes silently transfers to a materially changed question.
10. A corrected or deleted October movement updates October's measure and withdraws any proposal whose evidence no longer supports it. A confirmed household note remains in history with a visible **“Evidence changed; review this outcome”** flag.
11. A proposed win never appears under confirmed wins. A person can confirm, dismiss or later correct it; all linked evidence remains inspectable. A favourable metric trend alone does not create a win.
12. The monthly print/export view includes measure names, periods, local dates, units, completeness state and evidence links or IDs. Sensitive Medical and People notes are not copied into a general outcomes card.
