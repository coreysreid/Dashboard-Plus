# Core work needed for phone screens

Checked **21 November 2026** against decisions 0089 and 0100. The first phone screens in [FIRST_SCREENS.md](FIRST_SCREENS.md) are a design. Stage 1 provides stable record IDs and a local change log, but there is no phone member, pairing, transport, protected local accepted copy, durable outbox, per-operation Review staging, approval outcome pull, or phone navigation yet. Those are necessary before these screens can behave as written.

The main computer also needs a count-review contract that receives observed batch amount plus base revision, rechecks movements before correction, and returns a distinct needs-rework state. It needs stable operation IDs for idempotent retries, consistent accept/reject outcome timestamps, and a filtered member feed enforcing decision 0089's field rules. The phone must retain private local values across pulls without writing them into the portable log. A member cannot infer acceptance from send success.

No real iOS or Android device, screen reader, offline storage, OS notification, or private-network test was run for this draft. Do not call the copy or counts tested until the stage 2/3 build and real-device checks exist.
