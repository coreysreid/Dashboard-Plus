"""Keep fraud-grade details out (decision 0141): full card numbers, codes and passwords are refused, never stored.

Three checks, each with a plain message that says what to write instead and never repeats what was typed:

- every text value anywhere: a full payment card number (13 to 19 digits, starting 2 to 6 like the card networks,
  passing the card check digit) is refused, however it is spaced: any space, a line break, dots, slashes, dashes or
  underscores, and digits from any keyboard (decision 0143). A 13 or 14 digit shop barcode with a valid barcode
  check digit is not a card, nor is a pet's microchip (it starts 0, 1, 7, 8 or 9) or a phone's IMEI (15 digits
  starting 35). Also refused anywhere: a code, PIN or password written after its word ("alarm code 4321"), a full
  bank account (an IBAN, or a BSB, sort code or routing number with its account) and a tax, social security or
  health card number after its word, each with its own check digit where it has one (decision 0143);
- a column with `guard = "last_digits"` keeps only the last 4 digits of an account, policy or card number;
- a column with `guard = "where_kept"` says who to ask or where a code or password is kept, never the code.

`forbidden_field` is the check run when a module loads: no module may declare a column for a password, PIN,
code, full card or bank number, government ID number or a copy of an ID document.
"""
from __future__ import annotations

import re
import unicodedata

GUARDS = ("last_digits", "where_kept")
MASK = "••••"
# Put in place of a card number found in a spreadsheet the moment it is read, so the number itself never reaches a
# page, the browser or Review. A value holding it is refused like the number itself.
LEFT_OUT = "[card number left out]"

# A run of digit groups with one to three separators between groups (spaces, dots, slashes, dashes, underscores).
# Not part of a longer word or dashed identifier, so the digit groups of a record's permanent ID (a UUID such as
# 12345678-1234-...) are never taken for a card. Read on `_plain` text, where every kind of space is " ".
_RUN = re.compile(r"(?<![0-9A-Za-z-])(?<![0-9A-Za-z][_./])\d+(?:[ ./_-]{1,3}\d+)*"
                  r"(?![0-9A-Za-z])(?![-_./][0-9A-Za-z])")
_GROUP = re.compile(r"\d+")
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−﹣－"), "-")
_ZERO_WIDTH = "​‌‍⁠﻿᠎"

CARD = ("looks like a full card number. Dashboard Plus never keeps card numbers. Write only the last 4 digits, "
        f"e.g. {MASK}1234, or leave it out.")
LAST_DIGITS = f"keeps only the last 4 digits, e.g. {MASK}1234. Leave out the rest of the number."
WHERE_KEPT = ("says who to ask or where it is kept, such as “in the password manager” or “ask Alex next door”. Leave out "
              "the code, PIN or password itself.")
SECRET = ("looks like it holds a code, PIN or password. Dashboard Plus never keeps codes or passwords. Write who to "
          "ask or where it is kept, and leave the code itself out.")
BANK = (f"looks like a full bank account number. Dashboard Plus never keeps bank account numbers. Write only the last "
        f"4 digits, e.g. {MASK}5678, or where the details are kept.")
ID_NUMBER = ("looks like a tax, social security or health card number. Dashboard Plus never keeps ID numbers. Write "
             "where the card is kept instead, or leave it out.")
REFUSALS = (CARD, LAST_DIGITS, WHERE_KEPT, SECRET, BANK, ID_NUMBER)

# "pin 1234", "password: hunter2", "the code is 1-9-8-4": a secret written after the word that names it.
_SECRET_AFTER_WORD = re.compile(
    r"\b(?:password|passcode|passwd|pwd|pin|code|combination|combo|login|cvv2?|cvc2?)\b\s*(?:is|=|:|-|–)\s*\S",
    re.IGNORECASE)
_FOUR_DIGITS = re.compile(r"\d(?:[ .\-–]?\d){3,}")  # four or more digits, maybe split as 1-9-8-4
# A phone number in a "who to ask" field ("Ask Bob next door on 0491 570 156") is who to ask, not a code: one that
# starts with + or 0 and has 8 or more digits, or a North American 3-3-4 number with separators.
_PHONE = re.compile(r"(?<![0-9A-Za-z])(?:\+ ?\d|\(?0\d)[\d ().-]{6,20}\d(?![0-9A-Za-z])"
                    r"|(?<![0-9A-Za-z])\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![0-9A-Za-z])")

# Anywhere (decision 0143): a code, PIN or password written right after the word that names it. The word names a
# secret on its own (password, PIN, CVV) or is a lock's code ("alarm code", "gate code", "Wi-Fi password"); a bare
# "code" (post code, promo code) is not one. The secret is three or more digits ("alarm code 4321", "CVV 123"), or,
# for a password, the word after a colon or equals sign ("password: hunter2") or after "is" when it holds a digit.
_LOCKS = (r"(?:alarm|door|front ?door|back ?door|gate|side ?gate|safe|lock|padlock|garage|key ?safe|lock ?box|keypad"
          r"|access|entry|security|wi-?fi|router|network)")
_PASSWORD_WORDS = rf"(?:pass ?words?|passcodes?|passwd|pwd|{_LOCKS} ?(?:pass ?words?|passcodes?))"
_DIGIT_WORDS = (rf"(?:{_PASSWORD_WORDS}|pins?|pin numbers?|cvv2?|cvc2?|{_LOCKS} ?(?:codes?|pins?|combinations?)"
                r"|combinations?)")
_LEAD = r"(?:\s+(?:is|was|now|number|no\.?))*\s*(?:[:=#–-]\s*)?"
_NOT_A_SECRET = (r"(?:in|on|at|ask|see|kept|stored|written|with|under|from|the|a|my|our|their|its|same|none|n/?a"
                 r"|unknown|saved|behind|inside|changed|reset|by)\b")
_SECRET_IN_TEXT = re.compile(
    rf"\b{_DIGIT_WORDS}\b{_LEAD}\d(?:[ .\-–]?\d){{2,}}"
    rf"|\b{_PASSWORD_WORDS}\b\s*[:=]\s*(?!{_NOT_A_SECRET})\S"
    rf"|\b{_PASSWORD_WORDS}\s+is\s+(?=\S*\d)\S", re.IGNORECASE)

# A full bank account (decision 0143): an IBAN that passes its own check; or a BSB or sort code (six digits) or an
# ABA routing number (nine, passing its check) followed by an account number of five or more digits.
_IBAN = re.compile(r"(?<![0-9A-Za-z])[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}(?![0-9A-Za-z])")
_BRANCH_AND_ACCOUNT = re.compile(
    r"\b(?:bsb|sort ?code)\b[\s:#.-]*(?:\d{3}[ -]?\d{3}|\d{2}[ -]?\d{2}[ -]?\d{2})\b[^0-9]{0,30}?\d(?:[ -]?\d){4,}", re.IGNORECASE)
_ROUTING_AND_ACCOUNT = re.compile(
    r"\b(?:routing|aba)\b(?:\s*(?:number|no\.?|#))?[\s:#.-]*(\d{9})\b[^0-9]{0,30}?\d(?:[ -]?\d){4,}", re.IGNORECASE)

# A tax, social security or health card number after its word, with its own check digits (decision 0143).
_TFN = re.compile(r"\b(?:tfn|tax file(?: number| no\.?)?)\b[\s:#.-]*(\d(?:[ -]?\d){7,8})(?![0-9A-Za-z])",
                  re.IGNORECASE)
_SSN = re.compile(r"\b(?:ssn|social security(?: number| no\.?)?)\b[\s:#.-]*(\d{3})[ -]?(\d{2})[ -]?(\d{4})"
                  r"(?![0-9A-Za-z])", re.IGNORECASE)
_MEDICARE = re.compile(r"\bmedicare\b(?:\s*(?:card|number|no\.?))*[\s:#.-]*(\d(?:[ -]?\d){9,10})(?![0-9A-Za-z])",
                       re.IGNORECASE)
_NHS = re.compile(r"\bnhs\b(?:\s*(?:number|no\.?))?[\s:#.-]*(\d{3}[ -]?\d{3}[ -]?\d{4})(?![0-9A-Za-z])",
                  re.IGNORECASE)


def _plain(text: str) -> str:
    """The text with every digit as 0 to 9, every kind of space (non-breaking, thin, a line break) as " " and every
    dash as "-", one character for one, so a place found in it is the same place in what was typed (decision 0143)."""
    out = []
    for ch in text:
        if ch.isdecimal():
            out.append(str(unicodedata.decimal(ch)))
        elif ch.isspace() or ch in _ZERO_WIDTH:
            out.append(" ")
        else:
            folded = unicodedata.normalize("NFKC", ch)
            out.append(folded if len(folded) == 1 else ch)
    return "".join(out).translate(_DASHES)


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


def _card_groups(sizes: list[int]) -> bool:
    """True for the way cards are printed: groups of 4 with a shorter last group, or 4-6-5 (and 4-6-4)."""
    return (len(sizes) == 1 or (all(n == 4 for n in sizes[:-1]) and 1 <= sizes[-1] <= 4)
            or sizes in ([4, 6, 5], [4, 6, 4]))


def _is_card(digits: str) -> bool:
    # A phone's IMEI is 15 digits starting 35 with the same check digit; no card network issues such a number.
    return (digits[0] in "23456" and _luhn(digits) and not _barcode(digits)
            and not (len(digits) == 15 and digits.startswith("35")))


def card_numbers(text) -> list[tuple[int, int, str]]:
    """Every full card number in the text, as (start, end, digits only).

    A run of digit groups is read from its start, taking groups while they add up to 13 to 19 digits. Single
    spaces between groups may group the digits any way; any other separator (dots, slashes, dashes, two spaces)
    must group them as cards are printed, so dates (27/11/2026) and permanent IDs are never taken for a card."""
    if not isinstance(text, str) or not text:
        return []
    plain = _plain(text)
    found = []
    for match in _RUN.finditer(plain):
        groups = [(g.start() + match.start(), g.end() + match.start()) for g in _GROUP.finditer(match.group(0))]
        best = None
        for last in range(len(groups)):
            digits = "".join(plain[a:b] for a, b in groups[:last + 1])
            if len(digits) > 19:
                break
            if len(digits) < 13:
                continue
            separators = {plain[groups[i][1]:groups[i + 1][0]] for i in range(last)}
            if separators - {" "} and not _card_groups([b - a for a, b in groups[:last + 1]]):
                continue
            if _is_card(digits):
                best = (groups[0][0], groups[last][1], digits)
        if best:
            found.append(best)
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
    digits = re.sub(r"\D", "", _plain(text or ""))
    return digits[-4:] if len(digits) >= 4 else None


def _tfn(digits: str) -> bool:
    weights = (1, 4, 3, 7, 5, 8, 6, 9, 10) if len(digits) == 9 else (10, 7, 8, 4, 6, 3, 5, 1)
    return sum(int(d) * w for d, w in zip(digits, weights)) % 11 == 0


def _medicare(digits: str) -> bool:
    weighted = sum(int(d) * w for d, w in zip(digits, (1, 3, 7, 9, 1, 3, 7, 9)))
    return digits[0] in "23456" and weighted % 10 == int(digits[8])


def _nhs(digits: str) -> bool:
    check = 11 - sum(int(d) * (10 - i) for i, d in enumerate(digits[:9])) % 11
    return check != 10 and check % 11 == int(digits[9])


def _aba(digits: str) -> bool:
    return sum(int(d) * w for d, w in zip(digits, (3, 7, 1) * 3)) % 10 == 0


# Each country's IBAN length (the published IBAN registry). A random code or fingerprint that happens to start with
# two letters and two digits, such as a hash "de12...", is not an IBAN unless its country and length both fit.
_IBAN_LENGTHS = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16, "BG": 22, "BH": 22, "BR": 29, "BY": 28,
    "CH": 21, "CR": 22, "CY": 28, "CZ": 24, "DE": 22, "DK": 18, "DO": 28, "EE": 20, "EG": 29, "ES": 24, "FI": 18,
    "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23, "GL": 18, "GR": 27, "GT": 28, "HR": 21, "HU": 28, "IE": 22,
    "IL": 23, "IQ": 23, "IS": 26, "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32, "LI": 21, "LT": 20,
    "LU": 20, "LV": 21, "MC": 27, "MD": 24, "ME": 22, "MK": 19, "MR": 27, "MT": 31, "MU": 30, "NL": 18, "NO": 15,
    "PK": 24, "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22, "SA": 24, "SC": 31, "SE": 24, "SI": 19,
    "SK": 24, "SM": 27, "ST": 25, "SV": 28, "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22, "VG": 24, "XK": 20,
}


def _iban(candidate: str) -> bool:
    """True if an IBAN-shaped piece of text, or a shorter piece of it ending at a space, passes the IBAN check."""
    pieces = candidate.split(" ")
    for end in range(len(pieces), 0, -1):
        code = "".join(pieces[:end])
        if _IBAN_LENGTHS.get(code[:2]) != len(code):  # a real country code with that country's exact length
            continue
        moved = code[4:] + code[:4]
        if int("".join(str(int(ch, 36)) for ch in moved)) % 97 == 1:
            return True
    return False


def _upper_after_country(text: str) -> str:
    """The text with every letter in capitals except a two-letter word start, so the IBAN pattern (two capitals,
    two digits, then letters or digits) still finds an IBAN typed partly in lower case but keeps its country code
    as written."""
    return re.sub(r"(?<![0-9A-Za-z])([A-Za-z]{2})(\d{2})([ A-Za-z0-9]+)",
                  lambda m: m.group(1) + m.group(2) + m.group(3).upper(), text)


def _bank(plain: str) -> bool:
    # The country code must be written in capitals, as banks print it, so a lower-case fingerprint such as
    # "ad46c0..." is never read as an Andorran account; the rest may be typed in either case.
    if any(m.group(0)[:2].isupper() and _iban(m.group(0).upper())
           for m in _IBAN.finditer(_upper_after_country(plain))):
        return True
    if _BRANCH_AND_ACCOUNT.search(plain):
        return True
    return any(_aba(m.group(1)) for m in _ROUTING_AND_ACCOUNT.finditer(plain))


def _id_number(plain: str) -> bool:
    if any(_tfn(re.sub(r"\D", "", m.group(1))) for m in _TFN.finditer(plain)):
        return True
    for m in _SSN.finditer(plain):
        area, group, serial = m.groups()
        if area not in ("000", "666") and area[0] != "9" and group != "00" and serial != "0000":
            return True
    if any(_medicare(re.sub(r"\D", "", m.group(1))) for m in _MEDICARE.finditer(plain)):
        return True
    return any(_nhs(re.sub(r"\D", "", m.group(1))) for m in _NHS.finditer(plain))


def in_any_text(value) -> str | None:
    """The refusal for something no text may hold (decision 0141, widened by 0143), or None.

    A full card number, a code or password written after its word, a full bank account, or a tax, social security
    or health card number. The message never contains the value."""
    if not isinstance(value, str) or not value:
        return None
    if has_card_number(value):
        return CARD
    plain = _plain(value)
    if _SECRET_IN_TEXT.search(plain):
        return SECRET
    if _bank(plain):
        return BANK
    if _id_number(plain):
        return ID_NUMBER
    return None


def check(value: str, guard: str | None) -> str | None:
    """The refusal for a text value, or None if it may be kept. The message never contains the value."""
    if has_card_number(value):
        return CARD
    plain = _plain(value or "")
    if guard == "last_digits":
        # Up to 4 digits in all, at the end, after any words, dots, stars or x's: "1234", "••••1234",
        # "xxxx 1234", "ending 1234", "ends in 1234", "acct ending 1234".
        digits = re.sub(r"\D", "", plain)
        if not 1 <= len(digits) <= 4 or not re.search(r"\d[\s.)]*$", plain):
            return LAST_DIGITS
    elif guard == "where_kept":
        if _SECRET_AFTER_WORD.search(plain) or _SECRET_IN_TEXT.search(plain) \
                or _FOUR_DIGITS.search(_PHONE.sub(" ", plain)):
            return WHERE_KEPT
    return in_any_text(value)


def stored_last_digits(value: str) -> str:
    """How a `last_digits` field keeps what was typed: "••••1234"."""
    return MASK + re.sub(r"\D", "", _plain(value))[-4:]


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
