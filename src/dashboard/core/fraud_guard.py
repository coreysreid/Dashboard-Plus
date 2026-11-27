"""Keep fraud-grade details out (decision 0141): full card numbers, codes and passwords are refused, never stored.

Three checks, each with a plain message that says what to write instead and never repeats what was typed:

- every text value anywhere: a full payment card number (13 to 19 digits, spaces or dashes allowed, starting
  2 to 6 like the card networks, passing the card check digit) is refused. A 13 or 14 digit shop barcode with a
  valid barcode check digit is not a card, and neither is a pet's microchip (it starts 0, 1, 7, 8 or 9);
- a column with `guard = "last_digits"` keeps only the last 4 digits of an account, policy or card number;
- a column with `guard = "where_kept"` says who to ask or where a code or password is kept, never the code.

`forbidden_field` is the check run when a module loads: no module may declare a column for a password, PIN,
code, full card or bank number, government ID number or a copy of an ID document.
"""
from __future__ import annotations

import re

GUARDS = ("last_digits", "where_kept")
MASK = "••••"
# Put in place of a card number found in a spreadsheet the moment it is read, so the number itself never reaches a
# page, the browser or Review. A value holding it is refused like the number itself.
LEFT_OUT = "[card number left out]"

_RUN = re.compile(r"(?<![\d])\d(?:[ -]?\d){12,18}(?![\d])")  # 13 to 19 digits, single spaces or dashes between

CARD = ("looks like a full card number. Dashboard Plus never keeps card numbers. Write only the last 4 digits, "
        f"e.g. {MASK}1234, or leave it out.")
LAST_DIGITS = f"keeps only the last 4 digits, e.g. {MASK}1234. Leave out the rest of the number."
WHERE_KEPT = ("says who to ask or where it is kept, such as “in the password manager” or “ask Alex next door”. Leave out "
              "the code, PIN or password itself.")
REFUSALS = (CARD, LAST_DIGITS, WHERE_KEPT)

# "pin 1234", "password: hunter2", "the code is 1-9-8-4": a secret written after the word that names it.
_SECRET_AFTER_WORD = re.compile(
    r"\b(?:password|passcode|passwd|pwd|pin|code|combination|combo|login)\b\s*(?:is|=|:|-|–)\s*\S", re.IGNORECASE)
_FOUR_DIGITS = re.compile(r"\d(?:[ .\-–]?\d){3,}")  # four or more digits, maybe split as 1-9-8-4


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        total += d if i % 2 == 0 else (d * 2 - 9 if d > 4 else d * 2)
    return total % 10 == 0


def _barcode(digits: str) -> bool:
    """True for a 13 or 14 digit shop barcode (EAN-13, GTIN-14) whose own check digit is right."""
    if len(digits) not in (13, 14):
        return False
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def card_numbers(text) -> list[tuple[int, int, str]]:
    """Every full card number in the text, as (start, end, digits only)."""
    found = []
    for match in _RUN.finditer(text if isinstance(text, str) else ""):
        digits = re.sub(r"\D", "", match.group(0))
        if digits[0] in "23456" and _luhn(digits) and not _barcode(digits):
            found.append((match.start(), match.end(), digits))
    return found


def has_card_number(text) -> bool:
    """True if the text holds a full payment card number (or a spreadsheet cell that held one)."""
    return isinstance(text, str) and (LEFT_OUT in text or bool(card_numbers(text)))


def mask_cards(text):
    """The text with each card number shown only as its last 4 digits (••••1234). Anything else is unchanged."""
    if not isinstance(text, str) or not text:
        return text
    found = card_numbers(text)
    for start, end, digits in reversed(found):
        text = text[:start] + MASK + digits[-4:] + text[end:]
    return text


def leave_out_cards(text: str) -> str:
    """A spreadsheet's text with every card number replaced by LEFT_OUT, before anything shows or keeps it."""
    found = card_numbers(text)
    for start, end, _digits in reversed(found):
        text = text[:start] + LEFT_OUT + text[end:]
    return text


def last_digits(text) -> str | None:
    """The last 4 digits of a number as kept by a `last_digits` field ("1234"), or None if it has fewer than 4."""
    digits = re.sub(r"\D", "", text or "")
    return digits[-4:] if len(digits) >= 4 else None


def check(value: str, guard: str | None) -> str | None:
    """The refusal for a text value, or None if it may be kept. The message never contains the value."""
    if has_card_number(value):
        return CARD
    if guard == "last_digits":
        # Up to 4 digits, optionally after dots, stars or x's: "1234", "••••1234", "xxxx 1234", "ending 1234".
        rest = re.sub(r"(?i)^(?:ending(?: in)?|last 4|ends)\s*", "", value.strip())
        if not re.fullmatch(r"[•*xX.\s-]*\d{1,4}", rest):
            return LAST_DIGITS
    elif guard == "where_kept":
        if _SECRET_AFTER_WORD.search(value) or _FOUR_DIGITS.search(value):
            return WHERE_KEPT
    return None


def stored_last_digits(value: str) -> str:
    """How a `last_digits` field keeps what was typed: "••••1234"."""
    return MASK + re.sub(r"\D", "", value)[-4:]


# ----- what a module may never declare ------------------------------------------------------------------------

# Each: (pattern over a column's name or label, what it is, in plain words). Underscores count as spaces.
_FORBIDDEN = [
    (r"\bpass ?words?\b|\bpass ?codes?\b|\bpasswd\b|\bpwd\b|\blogins?\b", "a password or login"),
    (r"\bpins?\b|\bpin numbers?\b", "a PIN"),
    (r"\b(?:alarm|door|gate|safe|lock|garage|key ?safe|wi ?fi|wifi|access|entry|security|keypad)s? ?codes?\b"
     r"|\bcombinations?\b", "an alarm, door, safe, Wi-Fi or other access code"),
    (r"\bcvv\b|\bcvc\b|\bcard ?(?:number|no|num|expiry|expiry date)s?\b|\bcredit ?cards?\b|\bdebit ?cards?\b",
     "a payment card number, security code or expiry"),
    (r"\bbsb\b|\biban\b|\brouting\b|\bsort ?codes?\b|\bswift\b|\bbank ?accounts?\b"
     r"|\b(?:account|policy|member|membership|customer) ?(?:number|no|num)s?\b",
     "a full bank, account or policy number"),
    (r"\btax ?file\b|\btfn\b|\bssn\b|\bsocial ?security\b|\bmedicare\b|\bnational ?insurance\b|\bpassport ?(?:number|no)s?\b"
     r"|\blicen[cs]e ?(?:number|no)s?\b|\bid ?(?:number|no)s?\b|\bnational ?id\b",
     "a tax, social security, health card, passport, licence or other ID number"),
    (r"\bscans?\b|\bcopy of\b|\bphoto ?id\b|\bid ?(?:copy|copies|photo|photos|images?)\b",
     "a scan or copy of an ID document"),
    (r"\bsecurity ?(?:questions?|answers?)\b|\bmaiden ?names?\b", "a security question's answer"),
]
_FORBIDDEN = [(re.compile(p, re.IGNORECASE), what) for p, what in _FORBIDDEN]


def forbidden_field(words: str) -> str | None:
    """What fraud-grade detail a column name or label asks for, in plain words, or None if it asks for none."""
    text = re.sub(r"[_\-]+", " ", words or "")
    for pattern, what in _FORBIDDEN:
        if pattern.search(text):
            return what
    return None


def forbidden_problem(where: str, what: str) -> str:
    """The plain-language refusal a module author sees when a column asks for a fraud-grade detail."""
    return (f"{where}: this field would ask for {what}. Dashboard Plus never keeps passwords, PINs, codes, full card "
            f"or bank numbers, ID numbers or copies of ID (decision 0141). Ask instead who to call, where it is kept "
            f"(guard = \"where_kept\") or only its last 4 digits (guard = \"last_digits\").")


def unechoed(typed: dict, problems: dict) -> dict:
    """What a person typed, ready to put back on a form with its mistakes, without any value that was refused here:
    a refused card number, code or password is never sent back to the page (decision 0141)."""
    return {k: ("" if problems.get(k) in REFUSALS else v) for k, v in typed.items()}
