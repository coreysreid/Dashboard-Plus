"""Read and check a module's prompts.toml: "Have you thought about…?" questions, their groups and exact record matches."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

FILE = "prompts.toml"
SCHEMA = 1  # the version of the prompts.toml format below (decision 0104)
TOP_KEYS = ("schema", "answers", "group", "prompt")
GROUP_KEYS = ("key", "title")
PROMPT_KEYS = ("id", "group", "question", "why", "how_to_check", "fits", "answered_by", "match", "review_every",
               "source", "write_in")
# What a prompt may be matched to: only answers the household gave in Settings, never a guess from an address.
FITS_KEYS = ("storeys_min", "hazards", "pets", "mobility_needs", "country", "home_type")
MATCH_KEYS = ("table", "where", "filled", "positive")
SOURCE_KEYS = ("title", "url", "checked")
WRITE_IN_KEYS = ("table", "label")
ANSWERS = ("yes", "not_relevant", "not_yet")
# The columns a module's answers table must have, and the kinds each may be.
ANSWER_COLUMNS = {"prompt": ("text",), "answer": ("choice",), "answered_on": ("date",), "review_on": ("date",),
                  "note": ("text", "longtext"), "record": ("text",), "record_check": ("text",)}
PROMPT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Match:
    """Where a record that may already answer a prompt is looked for, and what it must hold."""
    table: str                      # "module.table", or "table" in the prompt's own module
    where: dict = field(default_factory=dict)     # path -> value or list of values ("item.category" = "water")
    filled: list = field(default_factory=list)    # paths that must not be blank; a link must reach a live record
    positive: list = field(default_factory=list)  # paths whose number must be above zero


@dataclass
class Prompt:
    id: str
    group: str
    question: str
    why: str
    fits: dict
    answered_by: str                # "module.table.field" or "none": the field that may help, as a person reads it
    review_every: int               # months, an editorial reminder, not an authority's deadline
    source: dict                    # {"title", "url", "checked"}
    how_to_check: str | None = None
    match: Match | None = None
    write_in: dict | None = None    # {"table", "label"}: a list where a plan can be written, never an answer


@dataclass
class PromptSet:
    module: str
    answers: str                    # the module's own table that keeps the household's answers
    groups: list = field(default_factory=list)    # [(key, title)] in the order shown
    prompts: list = field(default_factory=list)   # [Prompt] in the order written

    def get(self, prompt_id: str) -> Prompt | None:
        return next((p for p in self.prompts if p.id == prompt_id), None)

    def group_title(self, key: str) -> str:
        return dict(self.groups).get(key, key)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_answers_table(where: str, name, tables: dict, problems: list[str]) -> bool:
    table = tables.get(name) if isinstance(name, str) else None
    if table is None:
        problems.append(f"{where}: 'answers' must name a table of this module that keeps the answers.")
        return False
    ok = True
    for column, kinds in ANSWER_COLUMNS.items():
        found = table.columns.get(column)
        if found is None or found.type not in kinds or found.sensitive:
            problems.append(f"{where}: the answers table '{name}' needs an ordinary {' or '.join(kinds)} column "
                            f"'{column}'.")
            ok = False
    answer = table.columns.get("answer")
    if answer is not None and answer.type == "choice" and sorted(c.key for c in answer.choices) != sorted(ANSWERS):
        problems.append(f"{where}: the answers table's 'answer' choices must be exactly {', '.join(ANSWERS)}.")
        ok = False
    if table.suggestions:
        problems.append(f"{where}: the answers table '{name}' must say suggestions = false, so only a person "
                        f"answers a question.")
        ok = False
    return ok


def _check_fits(where: str, fits, problems: list[str]) -> dict:
    if not isinstance(fits, dict):
        problems.append(f"{where}: 'fits' must be a table such as {{ hazards = [\"flood\"] }}, or {{}}.")
        return {}
    for key in fits:
        if key not in FITS_KEYS:
            problems.append(f"{where}: 'fits' has an unknown setting '{key}'. Allowed: {', '.join(FITS_KEYS)}.")
    for key in ("hazards", "country", "home_type"):
        if key in fits and not (isinstance(fits[key], list) and fits[key] and all(_text(v) for v in fits[key])):
            problems.append(f"{where}: fits.{key} must be a list of words, like [\"flood\"].")
    for key in ("pets", "mobility_needs"):
        if key in fits and fits[key] is not True:
            problems.append(f"{where}: fits.{key} can only be true.")
    if "storeys_min" in fits and not (isinstance(fits["storeys_min"], int) and 2 <= fits["storeys_min"] <= 20):
        problems.append(f"{where}: fits.storeys_min must be a whole number from 2 to 20.")
    return {k: v for k, v in fits.items() if k in FITS_KEYS}


def _check_source(where: str, source, problems: list[str]) -> dict:
    if not isinstance(source, dict):
        problems.append(f"{where}: 'source' must say title, url and checked.")
        return {}
    for key in source:
        if key not in SOURCE_KEYS:
            problems.append(f"{where}: 'source' has an unknown setting '{key}'. Allowed: {', '.join(SOURCE_KEYS)}.")
    if not _text(source.get("title")):
        problems.append(f"{where}: source.title is missing (the public body and page, in plain words).")
    if not (isinstance(source.get("url"), str) and source["url"].startswith("https://")):
        problems.append(f"{where}: source.url must be an https:// link to the official page.")
    checked = source.get("checked")
    checked = checked.isoformat() if isinstance(checked, date) else checked
    try:
        if not (isinstance(checked, str) and ISO_DATE.match(checked)):
            raise ValueError
        date.fromisoformat(checked)
    except ValueError:
        problems.append(f"{where}: source.checked must be the date the source was checked, like \"2026-11-16\".")
        checked = None
    return {"title": source.get("title"), "url": source.get("url"), "checked": checked}


def _paths(where: str, name: str, raw, problems: list[str]) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(p, str) and 1 <= p.count(".") + 1 <= 2 for p in raw):
        problems.append(f"{where}: match.{name} must be a list of fields, each a column or link.column.")
        return []
    return list(raw)


def _check_match(where: str, module: str, raw, answered_by, problems: list[str]) -> Match | None:
    if not isinstance(raw, dict):
        problems.append(f"{where}: 'match' must say which table to look in.")
        return None
    for key in raw:
        if key not in MATCH_KEYS:
            problems.append(f"{where}: 'match' has an unknown setting '{key}'. Allowed: {', '.join(MATCH_KEYS)}.")
    table = raw.get("table")
    if not (isinstance(table, str) and 1 <= table.count(".") + 1 <= 2):
        problems.append(f"{where}: match.table must be a table, like \"medical.kits\".")
        return None
    if "." not in table:
        table = f"{module}.{table}"
    match_where = raw.get("where", {})
    if not isinstance(match_where, dict) or not all(isinstance(k, str) and k.count(".") <= 1 for k in match_where):
        problems.append(f"{where}: match.where must be a table of field = value, like {{ kind = \"smoke_alarm\" }}.")
        match_where = {}
    match = Match(table, dict(match_where), _paths(where, "filled", raw.get("filled", []), problems),
                  _paths(where, "positive", raw.get("positive", []), problems))
    if not match.filled and not match.positive:
        problems.append(f"{where}: 'match' needs at least one field in filled or positive.")
    if isinstance(answered_by, str) and answered_by != "none":
        mod, _, rest = answered_by.partition(".")
        tname, _, column = rest.partition(".")
        firsts = {p.split(".")[0] for p in match.filled + match.positive}
        if f"{mod}.{tname}" != match.table or column not in firsts:
            problems.append(f"{where}: answered_by '{answered_by}' must be a field that match checks in "
                            f"'{match.table}'.")
    return match


def load(folder: Path, module: str, tables: dict, read_toml, problems: list[str]) -> PromptSet | None:
    """Read `prompts.toml` if the module has one. Every mistake is added to `problems` in plain words."""
    path = Path(folder) / FILE
    if not path.exists():
        return None
    data = read_toml(path, problems, required=False)
    if not data:
        return None
    where = f"In {FILE}"
    for key in data:
        if key not in TOP_KEYS:
            problems.append(f"{where}: unknown setting '{key}'. Allowed: {', '.join(TOP_KEYS)}.")
    if data.get("schema") != SCHEMA:
        problems.append(f"{where}: 'schema' must be {SCHEMA}, the prompts format this program reads.")
    answers_ok = _check_answers_table(where, data.get("answers"), tables, problems)
    groups = []
    for number, raw in enumerate(data.get("group", []) if isinstance(data.get("group", []), list) else [], 1):
        if not isinstance(raw, dict) or not _text(raw.get("key")) or not _text(raw.get("title")) or \
                any(k not in GROUP_KEYS for k in raw):
            problems.append(f"{where}, group {number}: a group needs exactly a key and a title.")
            continue
        groups.append((raw["key"], raw["title"]))
    if len({k for k, _ in groups}) != len(groups):
        problems.append(f"{where}: two groups have the same key.")
    raw_prompts = data.get("prompt", [])
    if not isinstance(raw_prompts, list) or not raw_prompts:
        problems.append(f"{where}: no prompts are declared. Add at least one [[prompt]].")
        raw_prompts = []
    prompts, seen = [], set()
    for number, raw in enumerate(raw_prompts, 1):
        pid = raw.get("id") if isinstance(raw, dict) else None
        at = f"{where}, prompt {pid or number}"
        if not isinstance(raw, dict):
            problems.append(f"{at}: describe the prompt with id, group, question, why and source.")
            continue
        for key in raw:
            if key not in PROMPT_KEYS:
                problems.append(f"{at}: unknown setting '{key}'. Allowed: {', '.join(PROMPT_KEYS)}.")
        if not (isinstance(pid, str) and PROMPT_ID.match(pid)):
            problems.append(f"{at}: 'id' must use only lower-case letters, digits and hyphens.")
            continue
        if pid in seen:
            problems.append(f"{at}: another prompt already has this id.")
        seen.add(pid)
        if raw.get("group") not in dict(groups):
            problems.append(f"{at}: 'group' must be one of the groups: {', '.join(k for k, _ in groups)}.")
        for key in ("question", "why"):
            if not _text(raw.get(key)):
                problems.append(f"{at}: '{key}' is missing.")
        if "how_to_check" in raw and not _text(raw["how_to_check"]):
            problems.append(f"{at}: 'how_to_check' must be words when it is given.")
        every = raw.get("review_every")
        if not (isinstance(every, int) and not isinstance(every, bool) and 1 <= every <= 60):
            problems.append(f"{at}: 'review_every' must be a number of months from 1 to 60.")
        answered_by = raw.get("answered_by")
        if not (answered_by == "none" or (isinstance(answered_by, str) and answered_by.count(".") == 2)):
            problems.append(f"{at}: 'answered_by' must be \"none\" or a field written module.table.field.")
        match = None
        if "match" in raw:
            if answered_by == "none":
                problems.append(f"{at}: a prompt answered_by \"none\" cannot have a match.")
            else:
                match = _check_match(at, module, raw["match"], answered_by, problems)
        elif isinstance(answered_by, str) and answered_by != "none":
            problems.append(f"{at}: answered_by names a field, so 'match' must say exactly what that record "
                            f"must hold before it is offered.")
        write_in = raw.get("write_in")
        if write_in is not None and not (isinstance(write_in, dict) and set(write_in) == set(WRITE_IN_KEYS)
                                         and all(_text(v) for v in write_in.values())):
            problems.append(f"{at}: 'write_in' needs a table (module.table) and a label.")
            write_in = None
        prompts.append(Prompt(id=pid, group=str(raw.get("group")), question=str(raw.get("question", "")),
                              why=str(raw.get("why", "")), fits=_check_fits(at, raw.get("fits", {}), problems),
                              answered_by=str(answered_by), review_every=every if isinstance(every, int) else 12,
                              source=_check_source(at, raw.get("source"), problems),
                              how_to_check=raw.get("how_to_check"), match=match, write_in=write_in))
    if not answers_ok:
        return None
    return PromptSet(module=module, answers=data["answers"], groups=groups, prompts=prompts)


def _column_at(path: str, table, tables_of) -> object | None:
    """The column a path like "item.unit" ends at, or None. `tables_of(link)` gives a link's target table."""
    first, _, rest = path.partition(".")
    column = table.columns.get(first)
    if column is None or not rest:
        return column
    if column.type != "link":
        return None
    target = tables_of(column)
    return target.columns.get(rest) if target is not None else None


def cross_module_problems(prompt_set: PromptSet, by_name: dict) -> list[str]:
    """Check each match against the tables it names, once those modules are loaded.

    A match into a module that is not installed is fine: it simply finds nothing (decision 0104)."""
    problems = []
    for prompt in prompt_set.prompts:
        if prompt.match is None:
            continue
        where = f"In {FILE}, prompt {prompt.id}"
        mod, _, tname = prompt.match.table.partition(".")
        if mod not in by_name:
            continue
        table = by_name[mod].tables.get(tname)
        if table is None:
            problems.append(f"{where}: match.table '{prompt.match.table}' is not a table of the '{mod}' module.")
            continue

        def tables_of(column, mod=mod):
            other, _, name = column.to.partition(".") if "." in column.to else (mod, ".", column.to)
            return by_name[other].tables.get(name) if other in by_name else None

        for path in list(prompt.match.where) + prompt.match.filled + prompt.match.positive:
            first = table.columns.get(path.split(".")[0])
            if first is not None and "." in path and first.type == "link" and tables_of(first) is None:
                continue  # the link leads to a module that is not installed: the match finds nothing
            column = _column_at(path, table, tables_of)
            if column is None:
                problems.append(f"{where}: '{path}' is not a field of '{prompt.match.table}'.")
            elif path in prompt.match.positive and column.type not in ("integer", "decimal", "measure", "money"):
                problems.append(f"{where}: match.positive '{path}' must be a number.")
            elif path in prompt.match.where and column.type == "choice":
                wanted = prompt.match.where[path]
                for value in wanted if isinstance(wanted, list) else [wanted]:
                    if value not in [c.key for c in column.choices]:
                        problems.append(f"{where}: '{value}' is not one of the choices of '{path}'.")
        if prompt.write_in:
            other, _, name = prompt.write_in["table"].partition(".")
            if other in by_name and name not in by_name[other].tables:
                problems.append(f"{where}: write_in table '{prompt.write_in['table']}' does not exist.")
    return problems
