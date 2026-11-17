# Loan-register core needs

Checked **2026-11-17** against shipped People and Stock tables and `docs/DESIGN.md` sections 5 and 6. The examples are fictional; the due dates are household-entered agreements, not legal return periods. No outside fact or licence is used.

The present `expiring` watch cannot filter on `status = out`. Do **not** add a due-date watch until the core can limit it to active loans; otherwise a returned loan would continue to appear overdue. The open-loans list and sheet work now through a sheet `where` filter, but an ordinary table list cannot filter or sort by active status without core support. Needs attention should say **“Cordless drill: due back 26/11/26 from Dave Wilson”** only while the loan is out, using the household's date order.

The current generic form cannot require `returned_on` exactly when status is returned, clear it when reopened, or check `lent_on ≤ returned_on`. Add a one-step **“Mark returned”** action that records the date and status atomically and allows correction with an audit trail. Keep the earlier loan as history rather than deleting it. If a person lends the same item again, create a new loan. Do not decrement or restore Stock automatically without an explicit movement and a clear quantity rule; the link is for recognition only.

The borrower's phone stays in People and appears only through its existing privacy rules. There is no message-sending feature in this draft; a due date is a household reminder. The `borrower.phone` gap should be shown only for open loans and once per borrower, as in DESIGN 5.4.
