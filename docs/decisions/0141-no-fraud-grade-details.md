# 0141. No fraud-grade details: never ask for them, refuse them, tidy what was saved

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Claude (technical decision delegated by User 1, following User 1's rule below)

## In plain words
Dashboard Plus no longer keeps passwords, PINs, alarm or door codes, full card numbers or full account and policy
numbers. Where it used to ask for one, it now asks who to ask, where it is kept, or only the last 4 digits. If you
type a full card number anywhere, it is refused with what to write instead. Anything like that saved before is
hidden until you tidy it on a new page, **Tidy sensitive details**, which makes a backup first and has Undo.

User 1's rule, in their words: "To clarify the data should be consent based. Share whatever between users, but don't
store sensitive info in the app - passwords and digital copies of ID full credit card or bank account details etc.
that way there isn't a direct security risk for major fraud. Someone see you medication schedule isn't ideal but is
far less bad than getting all your legal docs and passwords."

The consent-based sharing part is decision 0140; this record is the "don't store it" part.

## What we chose

**1. The audit.** Every shipped module's `tables.toml`, `labels.toml`, `sheets.toml` and `prompts.toml`, and the
example households, were read for fields that invite fraud-grade data:

| Module | Table and column | What it was for | Decision |
|---|---|---|---|
| Home layout | exits, shutoffs, equipment, meters: `access_details` ("Codes or access details (private)") | alarm, door, key-safe codes | **Retired.** Replaced by `access_hint`, "Who to ask, or where the code is kept" (`guard = "where_kept"`) |
| Utilities | services: `account_number` | the full utility account number | **Retired.** A phone, internet or power account number is what is asked on the phone to change or move an account (and to port a phone number). Replaced by `account_last4` (`guard = "last_digits"`, private) |
| Bills and insurance | commitments: `reference` ("Account or policy reference") | the full policy or account number | **Retired.** A policy number is often enough to start a claim or change cover. Replaced by `reference_last4` (`guard = "last_digits"`, private) |
| People | important_info: `detail` when kind is "Access instructions" | how to get in | **Kept, guarded.** The kind now reads "Access: who to ask or where instructions are kept", and for that kind only (`guard_when`), a code, PIN or password is refused |
| Vehicles | vehicles: `registration` | the plate | **Kept** (private, never travels). It is printed on the car for anyone to see; it opens nothing |
| Pets | pets: `microchip` | finding a lost pet | **Kept.** A registry asks the owner to prove who they are; the number is on the vet's and registry's papers anyway |
| Documents | documents and copy places | where papers and their copies are | **Already safe** (decision 0062, 0090): no number, scan or copy field, and the expiry date only. No change |
| People | people: `birthday`, `address` | cards and visits | **Kept.** Useful every day and in User 1's "less bad" group; noted below as a downside |
| Readiness | prompts.toml | questions | **Already safe**: no question asks for a code or number |
| Every module | `notes`, `route`, `how_to_find` and other free text | anything | **Kept**, with the card check below; their help already says to leave codes out |

No module has a `file` column, so there is no upload of ID to remove.

**2. The design.** A module column may now say:
- `guard = "last_digits"`: only up to 4 digits are accepted ("1234", "••••1234", "ending 1234") and kept as
  "••••1234";
- `guard = "where_kept"`: who to ask or where the code is kept; four or more digits in a row (also "1-9-8-4") or a
  secret written after its word ("PIN 4821", "password: …", "the code is …") are refused;
- `guard_when = { kind = ["access"] }`: the guard applies only while that choice is chosen;
- `retired = { replaced_by = "…", note_to = "…", label = "…" }` on a private, never-travelling text column: it stays
  in the database for what was saved, and nothing else in the program ever sees it (it is taken out of the table's
  columns when the module loads, and out of every record the core reads).

**A checker at module load** refuses any non-retired column whose name or label asks for a password or login, PIN,
alarm/door/safe/Wi-Fi or other access code, card number, security code or expiry, BSB, IBAN, routing, sort code or
full account, policy, member or customer number, tax file, social security, Medicare, passport, licence or other ID
number, a scan or copy of ID, or a security answer. The module is left out with a plain sentence that names what it
would ask for and what to ask instead. A guarded column's label is not checked (its guard keeps it safe), but its
name still is.

**3. The input guard** sits in `Records.clean`, which every form, Mark done form, helper suggestion, spreadsheet
import and Bring in earlier entries already goes through. On every text value: 13 to 19 digits (single spaces or
dashes allowed) that start 2 to 6 like the card networks and pass the card check digit (Luhn) are refused, except a 13
or 14 digit shop barcode whose own barcode check digit is right. The refusal says "looks like a full card number …
Write only the last 4 digits, e.g. ••••1234". The message never contains the value, a refused form comes back with
that box empty, and nothing is logged. The helper API's whole-request screen (decision 0105) now uses the same check,
so it also catches 13 and 14 digit cards. A spreadsheet's card number is replaced by "[card number left out]" the
moment the file is read, so it never reaches the page, the browser or Review, and its row is refused.

**4. Existing data.** Three additive migrations add the new columns and keep the old ones with their values. Until
tidied, retired values are hidden everywhere (pages, sheets, export, helpers, sync), and a card number already saved
in ordinary text is shown, exported and sent to helpers only as ••••1234. Home says how many retired values wait.
**Tidy sensitive details** (`/tidy`) lists them by list, record and field with no value in the page; **Show what is
saved** (a pressed button, POST with the page token, never cached) shows them once. For each: **Keep only the last 4
digits**, **Write where it is kept instead** (into the replacing field, or a line added to Notes), or **Remove it**.
Each choice takes a backup first ("Before a sensitive detail was tidied", 30 kept), then changes the record in one
transaction as one history entry, which holds the old value only so that **Undo** works. **Forget the old values**
clears them from those entries and from the same fields in the record's earlier history.

**5.** Example households model the safe forms ("Ask Bob for the side gate code", last 4 digits only).

## Why we chose it
- User 1's rule: a copy of the data file, a backup or an export should not be enough for major fraud.
- One check in `Records.clean` covers every way in, so no screen can be forgotten.
- Retiring instead of dropping follows the data-safety rule: nothing a household saved is deleted without their
  choice, a backup and Undo.
- The checker makes the rule hold for modules written later, by Lane B or a household.

## What else we considered
- Dropping the old columns in a migration: loses data silently. Refused.
- Encrypting codes in the database: the key would sit beside it on the same computer; it moves the risk, not removes it.
- Keeping full numbers but private: they are still in every backup and copy of the file, which is the risk User 1 named.
- Refusing any long number anywhere: would refuse barcodes, microchips and phone numbers.

## What this costs us (the downsides)
- A household can no longer look up an account number or a door code here; they need their bill or password manager.
- The card check can be fooled by writing the number with letters or other separators, and about one in ten random
  13 to 19 digit numbers starting 2 to 6 passes the check digit, so a rare long serial number is refused too; the
  household can keep its last digits instead.
- The "where it is kept" check refuses any four digits in a row, so "Flat 1203" in a hint is refused.
- Access instructions saved before that hold a code stay behind Show (they were already private and local) until
  tidied; they are listed on the tidy page but not masked, because the form would otherwise save the mask.
- Old values stay in backups made before a tidy until those backups are replaced; the page says so.
- A card number in ordinary text that was already sent to the change log before this decision stays there; sync
  (decision 0140) is being built in parallel and has no paired computers yet.
- Birthdays and addresses are kept; together with a name they help identity fraud a little.

## How hard it is to undo
Medium. The guards are a few lines in `Records.clean`; the retired columns still hold their values until tidied, so
un-retiring is a tables.toml and labels.toml change. Tidied values come back only through Undo (before Forget) or a
backup.

## We should revisit this if
- Households report legitimate values refused (barcodes, serial numbers) often.
- A module needs a field the checker refuses and the safe forms do not fit.
- Sync (0140) starts carrying values: check that tidied and masked values travel as tidied.
