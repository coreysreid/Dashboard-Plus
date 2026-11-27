# 0143. Acting on the batch 23 privacy checks (decisions 0140 and 0141)

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
Lane B tried hard to store what must never be stored, acted as a helper with only the guide, and read the sharing page line by line. The worst thing it found: a card number copied from a bank page (with its invisible "non-breaking" spaces), or written with dots, slashes or two spaces, was kept as ordinary text, and a helper could send one. That is closed now. A code written after its word ("alarm code 4321"), a full bank account and a tax, social security or health card number are now refused in every box too, including notes and anything a helper sends, with the same plain words and never repeating what was typed.

## What we chose
**Card numbers, however they are written (item 116, worst first).** Before looking for a card, every digit from any keyboard (full-width phone digits too) is read as 0 to 9 and every kind of space (non-breaking, thin, a line break) as a space, one character for one, so a card is masked in exactly the right place. Between groups of digits up to three separators count: spaces, dots, slashes, dashes, underscores. Single spaces may group the digits any way, as before. Any other separator must group them the way cards are printed (fours with a shorter last group, or Amex's 4-6-5), so dates like 27/11/2026 04/12/2026 and a record's permanent ID (a UUID, decision 0141's fix) are never taken for a card. A run is read from its start, so "4111 1111 1111 1111 12/27" (a card and its expiry) is still found. A phone's IMEI (15 digits starting 35) is no longer refused as a card; no card network issues such a number, and Amex (34, 37) is still refused.

**Refused in every text, with their own plain words (items 114 and 116).** `fraud_guard.in_any_text` runs for every text value on forms, helper sends and imported rows when accepted:
- a code, PIN or password right after the word that names it: "alarm code 4321", "Gate PIN 4821", "CVV 123", "password: hunter2", "wifi password is blue42sky". A bare "code" (post code, promo code) is not a secret word, and "password: in the router drawer" or "the password is in the manager" are allowed;
- a full bank account: an IBAN that passes its own check (mod 97), or a BSB or sort code followed by an account number, or a routing number that passes its check followed by an account number. "BSB 062-000" alone is allowed: it names a branch, not an account;
- a tax file number, social security number, Medicare or NHS number after its word, each with its own check digits where it has them.

**Helpers (item 114).** These checks run on a helper's whole send before anything reaches Review: every value, notes, `why`, receipt lines. The refusal names the entry and field, never the value: "Entry 0, notes: this looks like it holds a code, PIN or password. …". A card keeps the error code `payment_detail`; the others use the new `never_kept`, in the published API description. The old refusal that blamed "receipt lines" is gone.

**Smaller fixes from the same reports.**
- "Who to ask" (`where_kept`) may hold the person's phone number ("Ask Bob next door on 0491 570 156"); "CVV 123" is refused there.
- "Last 4 digits" fields accept natural words: "ends in 1098", "last four 1098", "acct ending 1098".
- The helper guide says which way round this household writes dates ("day first (DD/MM/YY), so its 03/04/27 means 3 April 2027. Still send dates as 2027-04-03."), says a use-by date is never the day something was bought, and that a person's medicines go in their private medical details. Stock in and out's Date help says "never its use-by date".
- Review adds a gentle check under a suggested Stock in or out dated after today: "This date is after today. A Stock in is for something that already happened: check the date before accepting (a use-by date is not the day it was bought)." It only warns.
- Sharing (item 115): "(private)" is never said twice after a label that already says it (it could no longer happen with today's labels, since the codes column was retired by 0141, but the page now guards it). The page opens with "Jump to:" links to each part and says what is set differently from the usual ("You have changed 1 thing from the usual: People, Notes (Only on this computer).").
- A drill test's invented words held "back door code 4417"; that is now refused, as it should be, so the test says "back door tag 4417".

## Needs User 1
- **Medicines and medical details start Shared, and nobody is asked (item 115).** Decision 0140 kept 0089's choice that Medicine doses (with amounts) and medical details (allergies, conditions, medicines, care needs, diet) travel to a paired computer. The page says so honestly, so this is not a wrong statement, but your rule is "consent based". Should the first pairing ask "These private things are set to go to <computer>: … Share them or keep them here?" before the first full copy? Nothing travels yet, because pairing is not built.
- **Warn-then-allow for word-led numbers.** Lane B suggested a warning with "Keep it as typed" for passport and licence numbers, UK National Insurance numbers and "account 12345678" without a BSB. These have no check digit and "account" appears in ordinary notes (an electricity customer number), so refusing would block honest notes. A warning needs a new form step. Should we build it?

## Why we chose it
- Copying from a bank page or a PDF is the most likely way a real card number arrives, and it brings non-breaking spaces. A guard that misses it guards nothing.
- The same check on every path (forms, helpers, imports) means one set of plain words and no gap a helper can fall through.
- Requiring card-shaped groups for the new separators keeps dates, permanent IDs, phone lists and meter readings from becoming false alarms; check digits keep the bank and ID checks almost free of them.

## What else we considered
- Normalising the whole text with NFKC first: it can change the text's length (½ becomes three characters), so the masked card would land in the wrong place. One character for one keeps positions.
- Warning on Review instead of refusing a helper's send: the value would then already be stored in the waiting suggestion. Refusing keeps nothing.
- Refusing any "code" followed by digits: "post code 4000" and "Code 128 barcode" are ordinary.

## What this costs us (the downsides)
- A real note such as "Combination 4 of 6 bins" is fine, but "combination 123" is refused; a household must reword it.
- Old notes saved before this change that hold a code or bank number are not listed on Tidy sensitive details (it lists card numbers and retired fields). Editing such a record refuses until that note is fixed, with the same words.
- "Unit 1204 caretaker" in a "who to ask" field is still refused, since four digits in a row may be the code. Writing "Unit twelve-oh-four" or linking the person is the way round it.
- Helper sends that carried one of these into `why` are now refused whole; a helper must resend without it.

## How hard it is to undo
Easy. The checks are in `fraud_guard.py` (`_plain`, `card_numbers`, `in_any_text`) and the helper screen in `proposals._screen`; removing `in_any_text` from `check` restores card-only checking.

## We should revisit this if
- Households report honest notes refused (watch for "pin", "combination" and "security code").
- A new card network issues numbers outside 2 to 6, or 15-digit cards starting 35.
