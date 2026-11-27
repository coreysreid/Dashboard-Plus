# Batch 23 item 116: trying to store what must not be stored (0141)

Checked 27 November 2026 on Lane A's branch at `ac08f9d`, where decision 0141 is built. It is **not yet on
`main`**. Every number below is a published test card number or invented. Three ways in were tried:

- the shared check, `fraud_guard.check`, which every form, helper suggestion, import and Bring in goes through, with
  47 values in different spacings and formats;
- the **helper API** (`POST /api/v1/proposals`), with five sends;
- **forms** in the browser (Garcia copy): People notes and Home layout's "Who to ask, or where the code is kept".

## What gets through, worst first

### Important: a card number with other spacing is kept as ordinary text

The check finds 13 to 19 digits with **single** spaces or dashes only. All of these Visa test numbers were
**accepted** in a note, and the helper API accepted the first one as a waiting suggestion:

| Typed | Kept? |
|---|---|
| `4111 1111 1111 1111` with **non-breaking spaces** (what copying from a bank web page or PDF often gives) | **kept**; helper send accepted |
| `4111  1111  1111  1111` (two spaces) | kept |
| `4111.1111.1111.1111` | kept |
| `4111/1111/1111/1111`, `4111_1111_1111_1111` | kept |
| `4111 1111` on one line and `1111 1111` on the next | kept |
| a thin space (U+2009) between groups | kept |
| full-width digits `４１１１…` (some phone keyboards) | kept |

**Suggested change:** before looking for digit runs, turn every Unicode digit into 0 to 9. Treat any run of
whitespace (including U+00A0 and U+2000 to U+200B) and any of `. / _ -` as a separator, allowing one or two between
digits. Keep the Luhn and prefix rules so that the false-alarm rate does not rise. Add the table above as tests.

### Important: bank details, passwords and ID numbers in ordinary notes are kept

User 1's rule names "full credit card or bank account details" and passwords. 0141 guards only cards in ordinary
text; its own audit says free text is kept with the card check. These were **accepted** in People notes and through
the helper API:

| Typed | Kept? | Suggested check (warn, then refuse on a second press) |
|---|---|---|
| `BSB 062-000 account 12345678` | kept | the word BSB, then 6 digits (`\d{3}-?\d{3}`), then 6 or more digits |
| `GB82 WEST 1234 5698 7654 32` (IBAN) | kept | IBAN shape plus its mod-97 check: almost no false alarms, so refuse outright |
| `routing 021000021 acct 000123456789` | kept | "routing" or "ABA" with a 9-digit number passing the ABA check |
| `password: hunter2` | kept | 0141's own "secret after its word" rule, today only on `where_kept` fields |
| `Alarm code 4321` | kept | the same rule (also found in item 114 through a helper) |
| `TFN 123 456 782`, `SSN 078-05-1120`, `Medicare 2123 45670 1`, `NHS 943 476 5919` | kept | the word and a number of the right length; TFN, Medicare and NHS have check digits |
| `Passport PA1234567`, `Licence 12345678 NSW` | kept | the word and the number; warn only |

A **warning**, not a refusal, suits the word-led cases, because "code" and "account" appear in ordinary notes:
**"This looks like a bank account number. Dashboard Plus is not a place for full account numbers: keep only the last
4 digits (••••5678), or write where it is kept."** with **Change it** and **Keep it as typed**. The IBAN check can
refuse outright.

### Important (false alarm): a phone's IMEI is refused as a card

**"Old phone IMEI 353456789012348 for the insurer"** was refused on the People form with **"Notes looks like a full
card number."** The helper API also refused it. An IMEI is 15 digits, starts 35 and is built with the same check
digit (Luhn) as a card, so a real IMEI will always look like a card. Households keep IMEIs for insurance claims and
lost phones.

**Suggested change:** a 15-digit run that starts **35** and follows the word IMEI (or sits in a field labelled
IMEI or serial) is not a card. Better still, allow 15-digit numbers starting 35 or 01 (the IMEI ranges) unless the
word card, Visa or Mastercard is next to them. Amex is 15 digits but starts 34 or 37, so it stays refused.

### Important (false alarm): "Who to ask" cannot hold who to ask's phone number

On Home layout's ways out, **"Ask Bob next door on 0491 570 156"** was refused: **"Who to ask, or where the code is
kept says who to ask or where it is kept, such as “in the password manager” or “ask Alex next door”. Leave out the
code, PIN or password itself."**. The rule refuses four or more digits in a row, so a phone number, a unit number
("Unit 1204 caretaker") or a year is refused, in the very field that asks who to ask.

**Suggested change:** allow a value that is a phone number in the household's country format (the same reader
People uses). Or better: make "who to ask" a **link to People** beside the hint, so the number lives on the person.
Refusal words when it really looks like a code: **"This looks like the code itself. Write who to ask (choose them
from People) or where it is kept, and leave the code out."**

### Minor: the helper refusal blames receipt lines

A card number in a People **note**, or in the send's **why**, was refused with **"This request contains a long number
shaped like a payment card number. Leave card, loyalty and account numbers out of receipt lines and send it
again."**. The field was not a receipt line. Suggested: **"Entry 1, notes: this looks like a full card number.
Dashboard Plus never keeps card numbers. Send only the last 4 digits (••••1234), or leave it out."** Name the entry
and field, never the value.

### Minor: "last 4 digits" fields refuse natural ways of saying it

`account_last4` and `reference_last4` accept "1098", "ending 1098", "•••• 1098" and "xxxx-xxxx-1098", but refuse
**"ends in 1098"**, **"last four 1098"** and **"acct ending 1098"**. Suggested: accept any words before the last 1 to
4 digits, as long as there are no more than 4 digits in all.

### Minor: a card security code is accepted in a "where kept" field

"CVV 123" is three digits, so it passes the four-digit rule. Add `cvv|cvc|security code` to the
secret-after-its-word list.

## What held

- Single-spaced, dashed and plain card numbers were refused on the form, with **"…looks like a full card number.
  Dashboard Plus never keeps card numbers. Write only the last 4 digits, e.g. ••••1234, or leave it out."**, and the
  box came back empty, so the number was not echoed.
- Covered: Amex 4-6-5 grouping, Mastercard, a 13-digit Visa, a 19-digit Maestro, UnionPay 62, and groups of two
  digits. The helper API refused a card in `why` as well as in values.
- No false alarm on AU, US and UK phone numbers, two phones in a row, meter readings, an NMI (11 digits), a pet
  microchip (15 digits starting 9), a 13-digit EAN barcode, a 22-digit parcel tracking number, a 16-digit device
  serial that fails Luhn, or dates.
- `last_digits` fields kept only the last 4 digits; "Account 9876 5432 1098" was refused there.

## Not tried

The **Tidy sensitive details** page with old saved values, and spreadsheet import and Bring in through the browser.
Both use the same `card_numbers` function, so they share the spacing gap above. That should be confirmed with the
item 113 files after a fix.
