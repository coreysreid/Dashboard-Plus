# Helper and review acceptance checks

Use a synthetic helper called Receipt helper and a made-up Stock item. No real token is committed or printed in test output. The [flow](FLOW.md) contains exact screen wording.

1. **Narrow token.** Grant only `stock__movements`. The helper can read the allowed table spec and propose a Stock-in batch but cannot read or propose People rows. The Settings list shows the exact grant. Revoke the token and all later calls fail; existing queue/history remains.
2. **Private-by-default.** Without an explicit private-field grant, a helper cannot read or write a sensitive People or Medical field even if it can see that table. Settings clearly shows when such a grant is on.
3. **Bounded batch.** The helper proposes 12 rows from a fictional receipt, with a reason and request key. Review shows one batch with 12 row-level actions and a count, rather than silently adding 12 confirmed items. A request of 51 rows or a 201st row for that helper on the same day is refused under the design limits.
4. **Idempotent retry.** Retry the identical `request_key` from the same helper. The API returns the prior result and writes no new rows. A different helper may use the same key without colliding. A possible duplicate receipt with a new key is flagged for the person.
5. **Review words.** A proposed 4-tin addition against current 2 tins says “If you accept, it will say 6 tins.” Row actions are Accept, Change then accept, Reject. A batch accept cannot include two rows still needing a choice.
6. **Say no.** Reject one row and Reject all on another batch. Stock and unrelated records do not change; rejected rows remain in history and do not reappear on retry. A reason is optional.
7. **Change before accept.** Change a proposed quantity from 4 to 3 and accept. Stock adds 3, the change is attributed to the person, and the helper cannot amend or withdraw that row afterward.
8. **Stale proposal.** While Review is open, a person edits the target Stock item from 2 to 3. Accepting a proposed +4 after refresh shows a projected 7 and requires re-review; it never applies an obsolete absolute result of 6. A stale form post is refused and shows current values.
9. **Agent edit lock.** A helper attempts `/api/amend` and `/api/undo` on a person-edited or approved row. Both are refused; the record remains intact. It may amend or withdraw only its own still-unreviewed row.
10. **Atomic batch and undo.** A person accepts 11 of 12 rows and rejects one. Only 11 become confirmed Stock actions. Undo accepted batch reverses exactly those 11 when no later edits exist; if one was later edited, the conflict is shown and the person's edit is retained.
11. **Audit and source.** Each suggestion, decision and change is attributed to `agent:<name>` or the person as appropriate and has one batch ID. A helper cannot claim to be the person or bypass the review queue through another write route.
12. **Local scope.** The API binds to loopback only. A helper permission screen never implies the app itself contacts an outside service; a person who gives a token to one sees a clear warning about that service's access.
