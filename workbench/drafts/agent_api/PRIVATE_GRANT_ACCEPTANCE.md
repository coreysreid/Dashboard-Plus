# Future private-detail grant checks

Use only invented People details and Vehicle plates, **18 November 2026**. V1 still shares none.

1. Default Helpers Settings says **Private details: never shared**. A new helper, copied key or module grant alone returns no sensitive value from any v1 route or MCP tool.
2. A person selects exactly one declared sensitive field and confirms **Allow one read**; the review names the verified helper, record and field without including the value in initial HTML, URL or logs. Cancel creates no grant.
3. A helper lacking the module grant cannot receive a private grant for that module. A grant never enables private create/update/search/export or broad `/records` disclosure.
4. The intended helper uses the dedicated route once before expiry and receives only that field. A second read and another helper's attempt get a generic refusal; the read event is logged without value.
5. Expiry after 15 minutes, manual **Turn off access**, helper-key revocation and module switch-off each block a later read immediately. Settings shows Not read/Read/Expired/Turned off and last-read time accurately.
6. An edit to the approved private field, or deletion/restoration of its record, invalidates the grant. A new value requires a fresh person confirmation. Two changes in the same second are distinguished by a durable revision.
7. Two simultaneous reads consume the one-read grant exactly once. A response lost after consumption does not permit a silent retry; the household must grant again.
8. Restoring an older DB with an unused or already consumed grant cannot revive access. A mismatch between grant ledger and key file fails closed, without revealing whether a target record exists.
9. `/tables`, `/records`, `/attention`, `/batches`, Review, ordinary sheets and the eight v1 MCP tools still omit the detail. A direct guessed grant ID, query token, cookie or Origin-bearing request cannot read it.
10. Audit grant, read, denied identified read, expiry and revocation with identities, field name and time only. Scan audit, errors, backup status, logs and notifications for the invented private value and find none from grant handling.
11. Settings warns that an online helper may retain data already read. Revoking access stops new reads but does not promise to erase an outside copy; the household can inspect last-read history.
12. The grant handles both `people.important_info.detail` and `vehicles.vehicles.registration` without treating ordinary record names or linked IDs as private. A private value accidentally placed in an ordinary name is not silently protected by this grant design and must be reported separately.

Sources: v1 plan, decision 0059, `modules/people/tables.toml` and `modules/vehicles/tables.toml`, checked 18 November 2026. These are proposed checks, not current test results.
