"""Which "Have you thought about…?" questions fit the household, what may already be recorded, and how many were looked at.

Decision 0104. The questions are declared by modules in prompts.toml (core/prompts.py); the answers are
ordinary records in that module's own answers table, written through Records like any other, so history,
backups, export and the sync change log all cover them. Nothing here ever answers a question: a record
that matches is only offered to a person, who must choose Yes, Not relevant or Not yet.

Decision 0113: a Yes kept with a chosen record comes back only when a field its question lists in `ask_again`
changed. The check kept with the answer is a versioned field stamp: a hash of permanent IDs and of how many
times each listed field's value changed in the record's history, never the values themselves.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date

from dashboard.core import dates, db, settings, watch
from dashboard.core.prompts import ANSWERS, AskAgain, Prompt, PromptSet
from dashboard.core.records import Records, TableInfo, ValidationError
from dashboard.core.schema import table_name, target_table
from dashboard.core.sync import ID, REVISION

NOT_NOW_KEY = "questions.not_now"  # {"module:prompt": "until"}: cards set aside from Home, never an answer
NOT_NOW_DAYS = 7
HOME_LIMIT = 2  # at most two calm cards on Home at a time (Lane B's acceptance check 1)
STATES = ("to_look_at", "looked_at", "review", "does_not_fit")
# Decision 0113: the version of the check kept with an answer. A check without this prefix is decision 0104's
# fingerprint of whole-record revisions, read only to upgrade it. OFF_CHECK marks an answer whose record's module
# was switched off: it keeps asking again, even once the module is back, until a person answers.
CHECK_VERSION = "2"
CHECK_PREFIX = CHECK_VERSION + ":"
OFF_CHECK = CHECK_PREFIX + "module-off"


@dataclass
class Candidate:
    """A record that may already answer a question. Offered to a person; never an answer by itself."""
    table: str          # real table name
    record_id: int
    key: str            # "people__roles:<permanent ID>", what an answer keeps
    check: str          # the field stamp of the fields the question lists (decision 0113), never their words
    private: bool       # the match read a private detail: show only that a private record may relate
    row: dict
    legacy: str = ""    # decision 0104's revision fingerprint, read only to upgrade an older answer


@dataclass
class Question:
    module: str
    prompt: Prompt
    fits: bool
    not_fit_reasons: list = field(default_factory=list)
    answer: dict | None = None        # the current answer record, if any
    state: str = "to_look_at"
    review_reason: str | None = None  # "due", "record_changed" or "record_missing"
    due_on: str | None = None
    candidates: list = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.module}:{self.prompt.id}"


def prompt_sets(registry: dict[str, TableInfo]) -> dict[str, PromptSet]:
    """The question lists of the modules switched on, by module name."""
    found = {}
    for info in registry.values():
        prompts = info.module.prompts
        if prompts is not None and table_name(info.module.name, prompts.answers) in registry:
            found[info.module.name] = prompts
    return found


def answers_table(prompt_set: PromptSet) -> str:
    return table_name(prompt_set.module, prompt_set.answers)


# ----- does a question fit? -----------------------------------------------------------------------

def profile(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> dict:
    """The household's own answers in Settings that a question may be matched to. Nothing is guessed."""
    get = lambda key, default=None: settings.get(conn, f"household.{key}", default)  # noqa: E731
    return {"storeys": get("storeys"), "hazards": set(get("hazards", []) or []),
            "pets": watch.household(conn, registry).pets, "mobility_needs": bool(get("mobility_needs", False)),
            "country": get("country", "") or "", "home_type": get("home_type", "") or ""}


def fits(prompt: Prompt, home: dict, hazard_names: dict | None = None) -> list[str]:
    """Why a question does not fit the settings the household gave, as plain reasons; empty when it fits.

    Only a setting the household actually gave can rule a question out. Storeys and kind of home not given
    leave the question in; a hazard, pets, mobility needs or a country count only when the household said so."""
    return fits_rule(prompt.fits, home, hazard_names)


def fits_rule(rule: dict, home: dict, hazard_names: dict | None = None) -> list[str]:
    """The same as `fits` for any `fits` table, such as a drill's or one of its steps' (decision 0108)."""
    reasons = []
    names = hazard_names or {}
    storeys = home.get("storeys")
    if "storeys_min" in rule and storeys is not None and int(storeys) < rule["storeys_min"]:
        reasons.append(f"Settings say your home has {storeys} storey{'' if int(storeys) == 1 else 's'}.")
    if "hazards" in rule and not set(rule["hazards"]) & home["hazards"]:
        wanted = " or ".join(names.get(h, h) for h in rule["hazards"])
        reasons.append(f"{wanted} is not ticked under things that can happen where you live.")
    if rule.get("pets") and not home["pets"]:
        reasons.append("No pets are recorded.")
    if rule.get("mobility_needs") and not home["mobility_needs"]:
        reasons.append("Settings do not say that someone here has mobility or care needs.")
    if "country" in rule and home["country"] not in rule["country"]:
        reasons.append("It is written for another country." if home["country"] else
                       "Settings do not say which country you live in.")
    if "home_type" in rule and home["home_type"] and home["home_type"] not in rule["home_type"]:
        reasons.append("It is written for another kind of home.")
    return reasons


# ----- what may already be recorded -----------------------------------------------------------------

class _Reader:
    """Reads the rows a match follows, once each, noting every record it looked at."""

    def __init__(self, conn: sqlite3.Connection, registry: dict[str, TableInfo]):
        self.conn, self.registry = conn, registry
        self._rows: dict[tuple[str, int], dict | None] = {}
        self._history: dict[tuple[str, int], list] = {}

    def row(self, table: str, record_id) -> dict | None:
        key = (table, int(record_id))
        if key not in self._rows:
            found = self.conn.execute(f"SELECT * FROM {table} WHERE id = ?", key[1:]).fetchone()
            self._rows[key] = dict(found) if found is not None and not found["deleted_at"] else None
        return self._rows[key]

    def live_link(self, info: TableInfo, column, value, touched: set) -> tuple[TableInfo, dict] | None:
        """The live record a link points at (and, for a nested place, every place around it), or None."""
        target = self.registry.get(target_table(info.module.name, column))
        if target is None or value in (None, ""):
            return None
        row = self.row(target.name, value)
        if row is None:
            return None
        touched.add(_stamp(target.name, row))
        parent, seen = row.get(target.table.parent) if target.table.parent else None, {row["id"]}
        while parent not in (None, ""):  # "a linked full-path place": every place it sits inside is still there
            outer = self.row(target.name, parent)
            if outer is None or outer["id"] in seen:
                return None
            seen.add(outer["id"])
            touched.add(_stamp(target.name, outer))
            parent = outer.get(target.table.parent)
        return target, row

    def value(self, info: TableInfo, row: dict, path: str, touched: set):
        """(column, value, present) at a path like "place" or "item.unit"; present is False for a broken link."""
        first, _, rest = path.partition(".")
        column = info.table.columns[first]
        value = row.get(first)
        if not rest:
            if column.type == "link":
                return column, value, self.live_link(info, column, value, touched) is not None
            return column, value, True
        linked = self.live_link(info, column, value, touched)
        if linked is None:
            return None, None, False
        target, target_row = linked
        inner = target.table.columns[rest]
        if inner.type == "link":
            return inner, target_row.get(rest), self.live_link(target, inner, target_row.get(rest), touched) is not None
        return inner, target_row.get(rest), True


    # ----- field stamps (decision 0113) -----
    def history(self, table: str, record_id: int) -> list[tuple[str, dict, dict]]:
        """This record's history entries, oldest first, as (action, before, after). Read, never copied."""
        key = (table, int(record_id))
        if key not in self._history:
            self._history[key] = [
                (r["action"], json.loads(r["before"]) if r["before"] else {}, json.loads(r["after"]) if r["after"] else {})
                for r in self.conn.execute("SELECT action, before, after FROM core__audit WHERE table_name = ? AND "
                                           "record_id = ? ORDER BY id", key)]
        return self._history[key]

    def changes(self, table: str, record_id: int, column: str, normal) -> int:
        """How many times this field's value really changed (as `normal` sees it) since the record was made.
        Only ever goes up, so undoing an edit never makes an old check fit again."""
        return sum(1 for action, before, after in self.history(table, record_id)
                   if action == "update" and column in after and normal(before.get(column)) != normal(after[column]))

    def deletes(self, table: str, record_id: int) -> int:
        return sum(1 for action, _, _ in self.history(table, record_id) if action == "delete")

    def identity(self, info: TableInfo, row: dict) -> str:
        return f"{info.name}:{row.get(ID)}:deleted {self.deletes(info.name, row['id'])}"

    def link_parts(self, info: TableInfo, column, value) -> list[str]:
        """The record a link reaches and, for a nested place, every place around it: each one's name and what it
        sits inside (never its notes), so renaming or moving any place on the path asks again."""
        target = self.registry.get(target_table(info.module.name, column))
        row = self.row(target.name, value) if target is not None and value not in (None, "") else None
        if row is None:
            return [f"{column.name}->none"]
        parts = [self.identity(target, row)]
        parent = target.table.parent
        if parent:
            seen = set()
            while row is not None and row["id"] not in seen:
                seen.add(row["id"])
                parts.append(self.identity(target, row))
                for name in _name_columns(target) + [parent]:
                    parts.append(f"{target.name}:{row.get(ID)}:{name} {self.changes(target.name, row['id'], name, _normal)}")
                outer = row.get(parent)
                row = self.row(target.name, outer) if outer not in (None, "") else None
        return parts

    def stamp_parts(self, info: TableInfo, row: dict, path: str, normal) -> list[str]:
        """What one listed field adds to a stamp: its change count and, for a link, what the link reaches."""
        first, _, rest = path.partition(".")
        column = info.table.columns[first]
        if not rest:
            parts = [f"{path} {self.changes(info.name, row['id'], first, normal)}"]
            return parts + (self.link_parts(info, column, row.get(first)) if column.type == "link" else [])
        target = self.registry.get(target_table(info.module.name, column))
        linked = self.row(target.name, row.get(first)) if target is not None and row.get(first) not in (None, "") \
            else None
        if linked is None:
            return [f"{path} none"]
        inner = target.table.columns[rest]
        parts = [f"{path} {self.changes(target.name, linked['id'], rest, normal)}", self.identity(target, linked)]
        return parts + (self.link_parts(target, inner, linked.get(rest)) if inner.type == "link" else [])


def _name_columns(info: TableInfo) -> list[str]:
    """The columns a record is known by: those its record_name shows, else its name."""
    named = [n for n in re.findall(r"\{([a-z0-9_]+)", info.table.record_name or "") if n in info.table.columns]
    return list(dict.fromkeys(named)) or (["name"] if "name" in info.table.columns else [])


def _normal(value) -> str:
    """A value as compared for a field change: blank and missing are the same, spaces around text do not count."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _condition(reader: _Reader, prompt: Prompt, info: TableInfo, path: str):
    """For a field in ask_again.states: whether a value meets the match (above zero, or one of the listed values)."""
    if path in prompt.match.positive:
        def positive(value):
            try:
                return float(value) > 0
            except (TypeError, ValueError):
                return False
        return positive
    first, _, rest = path.partition(".")
    column = info.table.columns[first]
    if rest:
        target = reader.registry.get(target_table(info.module.name, column))
        column = target.table.columns[rest] if target is not None else None
    wanted = prompt.match.where[path]
    return lambda value: column is not None and _same(column, value, wanted)


def field_stamp(reader: _Reader, info: TableInfo, row: dict, prompt: Prompt) -> str:
    """The versioned field stamp of one record for one question (decision 0113): permanent IDs, how many times each
    listed field changed and how often each record was deleted, hashed. It holds no value, private or not."""
    ask = prompt.ask_again or AskAgain()
    parts = [reader.identity(info, row)]
    for path in ask.fields:
        parts += reader.stamp_parts(info, row, path, _normal)
    for path in ask.states:
        parts += [f"state {p}" for p in reader.stamp_parts(info, row, path, _condition(reader, prompt, info, path))]
    return CHECK_PREFIX + hashlib.sha256("|".join(sorted(set(parts))).encode()).hexdigest()[:24]


def _stamp(table: str, row: dict) -> str:
    return f"{table}:{row.get(ID)}:{row.get(REVISION)}"


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _same(column, value, wanted) -> bool:
    options = wanted if isinstance(wanted, list) else [wanted]
    if value is None:
        return False
    if column.type == "boolean":
        return any(bool(int(value)) == bool(w) for w in options)
    if column.type == "text":
        return str(value).strip().lower() in {str(w).strip().lower() for w in options}
    return value in options


def candidates(conn: sqlite3.Connection, registry: dict[str, TableInfo], prompt: Prompt) -> list[Candidate]:
    """Every live record that holds exactly what the prompt's match asks for. None for answered_by "none",
    for a module switched off or not installed, or for a record that fails any condition."""
    match = prompt.match
    if match is None:
        return []
    module, _, name = match.table.partition(".")
    info = registry.get(table_name(module, name))
    if info is None:
        return []
    paths = list(match.where) + match.filled + match.positive
    for path in paths:  # every table the match follows must be switched on too
        first, _, rest = path.partition(".")
        column = info.table.columns.get(first)
        if column is None or (rest and target_table(info.module.name, column) not in registry):
            return []
    reader, found = _Reader(conn, registry), []
    for raw in conn.execute(f"SELECT * FROM {info.name} WHERE deleted_at IS NULL ORDER BY id"):
        row, touched, private, ok = dict(raw), set(), False, True
        touched.add(_stamp(info.name, row))
        for path, wanted in match.where.items():
            column, value, present = reader.value(info, row, path, touched)
            if column is None or not present or not _same(column, value, wanted):
                ok = False
                break
        for path in match.filled if ok else []:
            column, value, present = reader.value(info, row, path, touched)
            if column is None or not present or _blank(value):
                ok = False
                break
            private = private or column.sensitive
        for path in match.positive if ok else []:
            column, value, present = reader.value(info, row, path, touched)
            try:
                ok = column is not None and present and float(value) > 0
            except (TypeError, ValueError):
                ok = False
            if not ok:
                break
        if ok:
            legacy = hashlib.sha256(",".join(sorted(touched)).encode()).hexdigest()[:20]
            found.append(Candidate(info.name, row["id"], f"{info.name}:{row.get(ID)}",
                                   field_stamp(reader, info, row, prompt), private, row, legacy))
    return found


def record_review(found: list[Candidate], record: str | None, check: str | None) -> str | None:
    """Why an answer kept with a chosen record needs looking at again, or None (decisions 0104 and 0113).

    "record_missing" when the record is deleted, stopped matching or its module is off; "record_changed" when a
    field its question lists changed, or its module was switched off since. An older answer's revision fingerprint
    still counts until the upgrade gives it a field stamp."""
    if not record:
        return None
    same = next((c for c in found if c.key == record), None)
    if same is None:
        return "record_missing"
    check = check or ""
    if check.startswith(CHECK_PREFIX):
        return None if check == same.check else "record_changed"
    return None if check == same.legacy else "record_changed"


# ----- answers and where each question stands -------------------------------------------------------

def current_answers(conn: sqlite3.Connection, prompt_set: PromptSet) -> dict[str, dict]:
    """The latest answer to each question, by prompt ID. Earlier answers live in each record's history."""
    found = {}
    for row in conn.execute(f"SELECT * FROM {answers_table(prompt_set)} WHERE deleted_at IS NULL "
                            f"ORDER BY answered_on, updated_at, id"):
        found[row["prompt"]] = dict(row)
    return found


def due_on(prompt: Prompt, answer: dict) -> str | None:
    """When an answer should be looked at again: the date the household chose, else the prompt's interval."""
    if answer.get("review_on"):
        return str(answer["review_on"])[:10]
    if answer.get("answered_on"):
        return dates.add_period(answer["answered_on"], prompt.review_every, "months")
    return None


def evaluate(conn: sqlite3.Connection, registry: dict[str, TableInfo], prompt_set: PromptSet,
             today: date | None = None, hazard_names: dict | None = None) -> list[Question]:
    """Every question of one module with where it stands today, in the order written."""
    today = today or date.today()
    home, answers, out = profile(conn, registry), current_answers(conn, prompt_set), []
    for prompt in prompt_set.prompts:
        reasons = fits(prompt, home, hazard_names)
        question = Question(prompt_set.module, prompt, not reasons, reasons, answers.get(prompt.id))
        question.candidates = candidates(conn, registry, prompt)
        answer = question.answer
        if answer is not None and answer.get("answer") in ANSWERS:
            question.due_on = due_on(prompt, answer)
            question.review_reason = record_review(question.candidates, answer.get("record"),
                                                   answer.get("record_check"))
            if question.review_reason is None and question.due_on and question.due_on <= today.isoformat():
                question.review_reason = "due"
            question.state = "review" if question.review_reason else "looked_at"
        if reasons:
            question.state = "does_not_fit"
        out.append(question)
    return out


def coverage(questions: list[Question], prompt_set: PromptSet) -> dict:
    """How many questions that fit have a current answer, in all and by group. A count, never a verdict."""
    def count(items):
        fitting = [q for q in items if q.fits]
        return {"fit": len(fitting), "looked_at": sum(1 for q in fitting if q.state == "looked_at")}
    groups = [dict(key=key, title=title, **count([q for q in questions if q.prompt.group == key]))
              for key, title in prompt_set.groups]
    return dict(total=len(questions), not_fit=sum(1 for q in questions if not q.fits), groups=groups,
                **count(questions))


def _set_aside(conn: sqlite3.Connection, today: date) -> dict:
    kept = settings.get(conn, NOT_NOW_KEY, {}) or {}
    return {k: v for k, v in kept.items() if isinstance(v, str) and v > today.isoformat()}


def not_now(conn: sqlite3.Connection, key: str, today: date | None = None) -> None:
    """Set a card aside from Home for a week. It is not an answer and changes no count."""
    today = today or date.today()
    kept = _set_aside(conn, today)
    kept[key] = date.fromordinal(today.toordinal() + NOT_NOW_DAYS).isoformat()
    settings.put(conn, NOT_NOW_KEY, kept)


def next_up(conn: sqlite3.Connection, registry: dict[str, TableInfo], limit: int = HOME_LIMIT,
            today: date | None = None) -> list[Question]:
    """A few questions worth a look now: ones to look at again first, then ones not answered yet."""
    today = today or date.today()
    aside, review, fresh = _set_aside(conn, today), [], []
    for prompt_set in prompt_sets(registry).values():
        for q in evaluate(conn, registry, prompt_set, today):
            if q.key in aside:
                continue
            (review if q.state == "review" else fresh if q.state == "to_look_at" else []).append(q)
    return (review + fresh)[:limit]


def save(store: Records, prompt_set: PromptSet, prompt_id: str, answer: str, review_on: str | None = None,
         note: str | None = None, record: str | None = None, today: date | None = None,
         actor: str = "person") -> int:
    """Save a person's answer to one question; return the answer record's id.

    One record per question: a new answer changes it and its history keeps the earlier ones. A record is
    kept only for Yes, and only when it is one the match offers right now; its fingerprint is kept with it,
    so a later change to that record brings the question back."""
    today = today or date.today()
    prompt = prompt_set.get(prompt_id)
    if prompt is None:
        raise ValidationError({"prompt": "is not one of the questions."})
    if answer not in ANSWERS:
        raise ValidationError({"answer": "choose Yes, Not relevant or Not yet."})
    chosen = None
    if record:
        offered = {c.key: c for c in candidates(store.conn, store.registry, prompt)}
        if answer != "yes" or record not in offered:
            raise ValidationError({"record": "that record cannot be used for this answer. Choose again."})
        chosen = offered[record]
    values = {"prompt": prompt_id, "answer": answer, "answered_on": today.isoformat(),
              "review_on": review_on or dates.add_period(today, prompt.review_every, "months"),
              "note": (note or "").strip() or None, "record": chosen.key if chosen else None,
              "record_check": chosen.check if chosen else None}
    existing = current_answers(store.conn, prompt_set).get(prompt_id)
    table = answers_table(prompt_set)
    if existing is not None:
        store.update(table, existing["id"], values, actor=actor)
        return existing["id"]
    return store.create(table, values, actor=actor)


# ----- keeping checks right when things change around them (decision 0113) ---------------------------------

def _answer_tables(prompt_set: PromptSet, registry: dict[str, TableInfo]) -> list[tuple[str, str, object]]:
    """(table, the column naming the question, how to find it) for answers and, with drills, practice answers."""
    found = [(answers_table(prompt_set), "prompt", prompt_set.get)]
    if prompt_set.run_steps and table_name(prompt_set.module, prompt_set.run_steps) in registry:
        found.append((table_name(prompt_set.module, prompt_set.run_steps), "step", prompt_set.step))
    return found


def upgrade_checks(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> int:
    """Give each answer still kept with decision 0104's revision fingerprint a field stamp; return how many.

    Only an answer whose record still matches and whose fingerprint still fits gets one, from the record as it is
    now. One that is already changed, deleted, no longer matching or whose module is off keeps its old check, so it
    stays in Review again until a person answers. No answer, date or chosen record changes and nothing is added to
    history: this is how the check is written, not a new answer. Run at start-up and after a restore, so a copy
    from before and a paired computer follow the same rule."""
    upgraded = 0
    with db.transaction(conn):
        for prompt_set in prompt_sets(registry).values():
            for table, column, lookup in _answer_tables(prompt_set, registry):
                offered = {}
                for row in conn.execute(f"SELECT id, {column} AS question, record, record_check FROM {table} "
                                        f"WHERE deleted_at IS NULL AND record IS NOT NULL AND record != '' AND "
                                        f"(record_check IS NULL OR record_check NOT LIKE ?)",
                                        (CHECK_PREFIX + "%",)).fetchall():
                    prompt = lookup(row["question"])
                    if prompt is None or prompt.match is None:
                        continue
                    if prompt.id not in offered:
                        offered[prompt.id] = {c.key: c for c in candidates(conn, registry, prompt)}
                    same = offered[prompt.id].get(row["record"])
                    if same is not None and row["record_check"] and row["record_check"] == same.legacy:
                        conn.execute(f"UPDATE {table} SET record_check = ? WHERE id = ?", (same.check, row["id"]))
                        upgraded += 1
    return upgraded


def upgrade_loaded(conn: sqlite3.Connection, loaded: list) -> int:
    """`upgrade_checks` with the modules switched on among those loaded (start-up and restore)."""
    from dashboard.core.records import build_registry
    on = settings.enabled_modules(conn)
    return upgrade_checks(conn, build_registry([m for m in loaded if m.name in on]))


def _modules_read(prompt: Prompt, info: TableInfo, registry: dict[str, TableInfo]) -> set[str]:
    """The modules whose records a question's match and ask_again read."""
    found = {info.module.name}
    ask = prompt.ask_again or AskAgain()
    for path in list(prompt.match.where) + prompt.match.filled + prompt.match.positive + ask.fields + ask.states:
        column = info.table.columns.get(path.split(".")[0])
        if column is not None and column.type == "link":
            found.add(target_table(info.module.name, column).split("__")[0])
    return found


def modules_switching_off(store: Records, names: set[str]) -> int:
    """Before modules are switched off: every answer kept with a record those modules hold, or read through,
    keeps asking again even once they are back on, until a person answers. Returns how many were marked."""
    marked = 0
    for prompt_set in prompt_sets(store.registry).values():
        for table, column, lookup in _answer_tables(prompt_set, store.registry):
            for row in store.conn.execute(f"SELECT id, {column} AS question, record_check FROM {table} WHERE "
                                          f"deleted_at IS NULL AND record IS NOT NULL AND record != ''").fetchall():
                prompt = lookup(row["question"])
                if prompt is None or prompt.match is None or row["record_check"] == OFF_CHECK:
                    continue
                mod, _, name = prompt.match.table.partition(".")
                info = store.registry.get(table_name(mod, name))
                if info is not None and _modules_read(prompt, info, store.registry) & set(names):
                    store.update(table, row["id"], {"record_check": OFF_CHECK}, actor="system")
                    marked += 1
    return marked
