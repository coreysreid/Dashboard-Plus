# Agent API skeleton: household journey check

Checked 19 November 2026 against `main` at `56aed78` (PR #123 merged). This is batch 13 item 54. All household names, places and keys used in the check were invented in a temporary data folder, which was not committed. Journey: M2 helper access in `docs/ROADMAP.md` and the eight-route plan in `docs/plans/agent-api-v1.md`.

## Finding, worst first

### Important: submitting “Make a key” twice leaves two active keys

**Where:** Settings → Helpers → Make a key.

**Steps:** With Household stock switched on, choose “Look only”, tick Household stock, enter “Repeat helper”, and choose **Make a key**. Submit that same form again, as can happen if someone refreshes the key page and agrees to resend the form. Return to Helpers.

**Expected:** The second submission does not create another active grant. The person can tell what happened and deliberately start a new form if they really want another key.

**Actual:** Both submissions returned HTTP 201 with distinct keys. Helpers then listed two active “Repeat helper” rows. Both grants remain until individually turned off. The shared page token checks that the request came from Dashboard, but it does not make a form submission one-use.

**Suggested change:** Give each displayed Make a key form a one-use submission token. Consume it with the first successful grant; on a repeat submission, do not issue another key. Show: **“A key was already made from this form. It cannot be shown again. Return to Helpers if you want to make another.”** Keep the existing key page for the first submission, since that is the only time the key can be shown. Acceptance check: submit identical form data twice, verify one helper row and one live key, then start a fresh form and verify a new intentional grant can be made.

## Journey that passed

I started the merged app on `127.0.0.1:5129` with a temporary Household stock setup, signed into its pages, and used its real HTTP endpoints. No helper key appears in this report.

1. Settings → Helpers showed the current local API address and no part ticked by default. Making “Pantry helper” with “Look and suggest” and Household stock returned HTTP 201. The key appeared on that response and was absent when I revisited Helpers.
2. `curl` with `Authorization: Bearer` reached `/api/v1/me` and `/api/v1/tables` (both 200); the helper saw only its granted part. `stock__places` was described as suggestible.
3. A JSON POST to `/api/v1/proposals` proposed two invented places and returned 201 with both waiting. Neither place was in the ordinary list before Review. Review displayed both names and the helper's reason.
4. Accepting one row and rejecting the other each redirected normally (302). The accepted place appeared in Stock Places; the rejected place did not.
5. Turning off access from Helpers redirected normally (302). The same bearer key then got 401 `no_key` from `/api/v1/me`.

**Limit:** This check used one temporary Stock household and a local curl client. The broader three-household, narrow-screen check is batch 14 item 55; the household connection guide is item 60.
