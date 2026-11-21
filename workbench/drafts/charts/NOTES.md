# Core needs before chart promotion

**21 November 2026 recheck:** [FIRST_TWO.md](FIRST_TWO.md) selects today's drinking-water breakdown and one pet's weigh-ins as the first two. The older water-over-time, waste, annotated pet and month-end Readiness sketches below remain future options. Readiness questions now ship (0104); they still need comparable month-end snapshots for a historical chart. Stock spend remains a design in batch 20 item 92, not a shipped price source.

Checked **2026-11-17** against shipped modules and `docs/DESIGN.md` section 10.

1. **History:** Keep dated Stock balances or a reliable starting count plus all movements and corrections. Today's item quantity alone cannot draw a trustworthy past water line or shortage story. Keep the movement-time unit and the household-size/basis history used for water days.
2. **Completeness:** Store household-confirmed full months for waste. An empty month is unknown until confirmed. Make late edits recalculate the chart and evidence table.
3. **Annotations:** Add person-confirmed, subject-linked event markers. Proximity alone must not label an event as an explanation. Pets weigh-ins can draw points now, but question-loop inference needs about 20 usable observations and the DESIGN guardrails.
4. **Readiness:** The prompt engine needs versioned questions, applicability, answer history and month-end snapshots. No matching record automatically counts as an answer.
5. **Chart component:** Provide a keyboard and touch operable period selector and detail view, visible focus, accessible text/table equivalent, and no colour-only distinctions. Preserve a readable print/export table. Reuse one chart component for the four shapes instead of bespoke screens.

No external facts or licences are needed for these internal product sketches.
