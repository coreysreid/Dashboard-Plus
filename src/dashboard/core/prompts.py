"""Read and check a module's prompts.toml: "Have you thought about…?" questions, their groups, exact record matches and "Think it through" drills."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

FILE = "prompts.toml"
SCHEMA = 3  # the newest version of the prompts.toml format below (decisions 0104, 0108 and 0113)
# 1: questions only (0104); 2: also drills ([[scenario]], [[step]], [[emergency]], runs); 3: every match also says
# `ask_again`, the fields whose change brings a confirmed answer back (0113).
SCHEMAS = (1, 2, 3)
TOP_KEYS = ("schema", "answers", "group", "prompt")
DRILL_KEYS = ("runs", "run_steps", "scenario", "step", "emergency")  # schema 2 and 3 only
GROUP_KEYS = ("key", "title")
PROMPT_KEYS = ("id", "group", "question", "why", "how_to_check", "fits", "answered_by", "match", "ask_again",
               "review_every", "source", "write_in")
# Schema 2: the exact words a drill step shows when nothing is recorded, a caution shown with any record it
# offers, and a supply (module.table with a days-of-cover rule) whose working it shows. A [[prompt]] used as
# a shared drill step may say them too.
STEP_TEXT_KEYS = ("missing", "caution", "supply")
STEP_KEYS = ("id", "question", "why", "fits", "answered_by", "match", "ask_again") + STEP_TEXT_KEYS
SCENARIO_KEYS = ("id", "version", "title", "intro", "fits", "sources", "steps", "review_every")
SCENARIO_FITS_KEYS = ("has_records",)  # the household has at least one record in this table ("module.table")
EMERGENCY_KEYS = ("country", "number", "source")
# What a prompt may be matched to: only answers the household gave in Settings, never a guess from an address.
FITS_KEYS = ("storeys_min", "hazards", "pets", "mobility_needs", "country", "home_type")
MATCH_KEYS = ("table", "where", "filled", "positive")
# Schema 3 (decision 0113): which changes to a chosen record bring a confirmed answer back. `fields` are compared
# by value (a link also covers the record it reaches and, for a nested place, every place around it: their names
# and what each sits inside); `states` only by whether they still meet the match (a positive amount, a unit of the
# listed kind), so using one litre from a batch that still has some left changes nothing.
ASK_AGAIN_KEYS = ("fields", "states")
SOURCE_KEYS = ("title", "url", "checked")
WRITE_IN_KEYS = ("table", "label")
ANSWERS = ("yes", "not_relevant", "not_yet")
# The columns a module's answers table must have, and the kinds each may be.
ANSWER_COLUMNS = {"prompt": ("text",), "answer": ("choice",), "answered_on": ("date",), "review_on": ("date",),
                  "note": ("text", "longtext"), "record": ("text",), "record_check": ("text",)}
# The columns of a module's practice-run tables (decision 0108). Own words are private and never travel.
RUN_COLUMNS = {"scenario": ("text",), "scenario_version": ("integer",), "started_on": ("date",),
               "practised_on": ("date",), "review_on": ("date",), "status": ("choice",)}
RUN_STATUSES = ("in_progress", "practised")
STEP_COLUMNS = {"run": ("link",), "step": ("text",), "choice": ("choice",), "own_words": ("text", "longtext"),
                "record": ("text",), "record_check": ("text",)}
STEP_CHOICES = ("plan", "check", "not_relevant")
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
class AskAgain:
    """The fields of a chosen record whose change brings a confirmed answer back (decision 0113)."""
    fields: list = field(default_factory=list)   # paths compared by value: "place", "person.phone"
    states: list = field(default_factory=list)   # paths compared only by whether they meet the match: "quantity"


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
    ask_again: AskAgain | None = None  # with every match; older files ask again for the fields the match reads
    write_in: dict | None = None    # {"table", "label"}: a list where a plan can be written, never an answer
    missing: str | None = None      # schema 2: the exact words shown when no record matches
    caution: str | None = None      # schema 2: shown with any record offered, e.g. a door is not a checked route
    supply: str | None = None       # schema 2: "module.table" whose days-of-cover working the step shows


@dataclass
class Scenario:
    """A "Think it through" drill: a calm, ordered run of questions about one invented situation (0108)."""
    id: str
    version: int                    # raise it when the steps or wording change; earlier runs keep theirs
    title: str
    intro: str
    fits: dict                      # the settings a prompt fits, plus has_records
    sources: list                   # [{"title", "url", "checked", "country": [...] or None, "needs_checking"}]
    steps: list                     # prompt or step IDs, in order
    review_every: int = 12          # months offered as the "look again on" date: an editorial suggestion


@dataclass
class PromptSet:
    module: str
    answers: str                    # the module's own table that keeps the household's answers
    groups: list = field(default_factory=list)    # [(key, title)] in the order shown
    prompts: list = field(default_factory=list)   # [Prompt] in the order written
    runs: str | None = None         # schema 2: the module's table of practice runs
    run_steps: str | None = None    # schema 2: the module's table of each run's step answers
    scenarios: list = field(default_factory=list)  # [Scenario] in the order written
    steps: list = field(default_factory=list)      # [Prompt]: drill-only steps, never listed as questions
    emergency: dict = field(default_factory=dict)  # country -> {"number", "source"}

    def get(self, prompt_id: str) -> Prompt | None:
        return next((p for p in self.prompts if p.id == prompt_id), None)

    def group_title(self, key: str) -> str:
        return dict(self.groups).get(key, key)

    def step(self, step_id: str) -> Prompt | None:
        """A drill step: a drill-only step, or a shared question whose answer also counts on Questions."""
        return next((p for p in self.steps if p.id == step_id), None) or self.get(step_id)

    def is_shared(self, step_id: str) -> bool:
        return self.get(step_id) is not None

    def scenario(self, scenario_id: str) -> Scenario | None:
        return next((s for s in self.scenarios if s.id == scenario_id), None)


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_columns(where: str, name, tables: dict, wanted: dict, what: str, problems: list[str],
                   private: tuple = ()) -> object | None:
    """The table `name` of this module with every column in `wanted`; only `private` columns may be private."""
    table = tables.get(name) if isinstance(name, str) else None
    if table is None:
        problems.append(f"{where}: '{what}' must name a table of this module.")
        return None
    ok = True
    for column, kinds in wanted.items():
        found = table.columns.get(column)
        if found is None or found.type not in kinds or (found.sensitive and column not in private):
            problems.append(f"{where}: the table '{name}' needs an ordinary {' or '.join(kinds)} column "
                            f"'{column}'.")
            ok = False
    if table.suggestions:
        problems.append(f"{where}: the table '{name}' must say suggestions = false, so only a person "
                        f"answers a question.")
        ok = False
    return table if ok else None


def _check_choices(where: str, table, column: str, wanted: tuple, problems: list[str]) -> bool:
    found = table.columns.get(column)
    if found is not None and found.type == "choice" and sorted(c.key for c in found.choices) != sorted(wanted):
        problems.append(f"{where}: the '{column}' choices of '{table.name}' must be exactly {', '.join(wanted)}.")
        return False
    return True


def _check_answers_table(where: str, name, tables: dict, problems: list[str]) -> bool:
    table = _check_columns(where, name, tables, ANSWER_COLUMNS, "answers", problems)
    return table is not None and _check_choices(where, table, "answer", ANSWERS, problems)


def _check_run_tables(where: str, data: dict, tables: dict, problems: list[str]) -> bool:
    """The practice-run tables a module with drills keeps (decision 0108). Own words must be private and stay
    on this computer: they are about who is home, security and health, so they never travel or export."""
    runs = _check_columns(where, data.get("runs"), tables, RUN_COLUMNS, "runs", problems)
    steps = _check_columns(where, data.get("run_steps"), tables, STEP_COLUMNS, "run_steps", problems,
                           private=("own_words",))
    ok = runs is not None and steps is not None
    if runs is not None:
        ok = _check_choices(where, runs, "status", RUN_STATUSES, problems) and ok
    if steps is not None:
        ok = _check_choices(where, steps, "choice", STEP_CHOICES, problems) and ok
        words = steps.columns["own_words"]
        if not words.sensitive or words.travels != "never" or not words.travels_reviewed:
            problems.append(f"{where}: own_words in '{data.get('run_steps')}' must say sensitive = true and "
                            f"travels = \"never\", so a household's own words stay on this computer.")
            ok = False
        if steps.columns["run"].to != data.get("runs"):
            problems.append(f"{where}: 'run' in '{data.get('run_steps')}' must link to the runs table.")
            ok = False
    return ok


def _check_fits(where: str, fits, problems: list[str], extra: tuple = ()) -> dict:
    allowed = FITS_KEYS + extra
    if not isinstance(fits, dict):
        problems.append(f"{where}: 'fits' must be a table such as {{ hazards = [\"flood\"] }}, or {{}}.")
        return {}
    for key in fits:
        if key not in allowed:
            problems.append(f"{where}: 'fits' has an unknown setting '{key}'. Allowed: {', '.join(allowed)}.")
    for key in ("hazards", "country", "home_type"):
        if key in fits and not (isinstance(fits[key], list) and fits[key] and all(_text(v) for v in fits[key])):
            problems.append(f"{where}: fits.{key} must be a list of words, like [\"flood\"].")
    for key in ("pets", "mobility_needs"):
        if key in fits and fits[key] is not True:
            problems.append(f"{where}: fits.{key} can only be true.")
    if "storeys_min" in fits and not (isinstance(fits["storeys_min"], int) and 2 <= fits["storeys_min"] <= 20):
        problems.append(f"{where}: fits.storeys_min must be a whole number from 2 to 20.")
    if "has_records" in fits and not (isinstance(fits["has_records"], str) and fits["has_records"].count(".") == 1):
        problems.append(f"{where}: fits.has_records must be a table, like \"vehicles.vehicles\".")
    return {k: v for k, v in fits.items() if k in allowed}


def _checked(source: dict) -> str | None:
    checked = source.get("checked")
    checked = checked.isoformat() if isinstance(checked, date) else checked
    try:
        if not (isinstance(checked, str) and ISO_DATE.match(checked)):
            raise ValueError
        date.fromisoformat(checked)
    except ValueError:
        return None
    return checked


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
    checked = _checked(source)
    if checked is None:
        problems.append(f"{where}: source.checked must be the date the source was checked, like \"2026-11-16\".")
    return {"title": source.get("title"), "url": source.get("url"), "checked": checked}


def _scenario_source(where: str, source, problems: list[str]) -> dict | None:
    """A drill's source. A broken link or date is kept and shown as "Source needs checking" (Lane B's check
    12), never dropped or swapped for unsourced advice; only a missing title stops the module loading."""
    if not isinstance(source, dict) or not _text(source.get("title")):
        problems.append(f"{where}: each source needs a title (the public body and page), url and checked date.")
        return None
    for key in source:
        if key not in SOURCE_KEYS + ("country",):
            problems.append(f"{where}: a source has an unknown setting '{key}'.")
    country = source.get("country")
    if country is not None and not (isinstance(country, list) and country and all(_text(c) for c in country)):
        problems.append(f"{where}: a source's country must be a list of countries, like [\"Australia\"].")
        country = None
    url = source.get("url") if isinstance(source.get("url"), str) else ""
    checked = _checked(source)
    return {"title": source["title"], "url": url, "checked": checked, "country": country,
            "broken": not url.startswith("https://") or checked is None}


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


def _check_ask_again(at: str, raw, match: Match, problems: list[str]) -> AskAgain:
    """The fields whose change asks again. Every field the match reads must be listed, so a record that stopped
    matching and matches again still asks; a linked field needs its link listed too."""
    if not isinstance(raw, dict) or "fields" not in raw:
        problems.append(f"{at}: 'ask_again' must list the fields whose change asks again, like "
                        f"{{ fields = [\"place\"] }}.")
        return _default_ask_again(match)
    for key in raw:
        if key not in ASK_AGAIN_KEYS:
            problems.append(f"{at}: 'ask_again' has an unknown setting '{key}'. Allowed: {', '.join(ASK_AGAIN_KEYS)}.")
    lists = {}
    for key in ASK_AGAIN_KEYS:
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(p, str) and 1 <= p.count(".") + 1 <= 2 for p in value) \
                or len(set(value)) != len(value):
            problems.append(f"{at}: ask_again.{key} must be a list of different fields, each a column or link.column.")
            value = []
        lists[key] = list(value)
    ask = AskAgain(lists["fields"], lists["states"])
    if not ask.fields:
        problems.append(f"{at}: ask_again.fields must name at least one field.")
    both = set(ask.fields) & set(ask.states)
    if both:
        problems.append(f"{at}: '{sorted(both)[0]}' is in both ask_again.fields and ask_again.states.")
    for path in ask.states:
        if path not in match.where and path not in match.positive:
            problems.append(f"{at}: ask_again.states '{path}' must be a field in match.where or match.positive.")
    listed = set(ask.fields) | set(ask.states)
    for path in list(match.where) + match.filled + match.positive:
        if path not in listed:
            problems.append(f"{at}: ask_again must list '{path}', a field the match reads.")
    for path in sorted(listed):
        if "." in path and path.split(".")[0] not in ask.fields:
            problems.append(f"{at}: ask_again lists '{path}', so it must list the link '{path.split('.')[0]}' "
                            f"in fields too.")
    return ask


def _default_ask_again(match: Match) -> AskAgain:
    """For a schema 1 or 2 file: ask again when anything the match reads changes."""
    fields = []
    for path in list(match.where) + match.filled + match.positive:
        for part in ([path.split(".")[0]] if "." in path else []) + [path]:
            if part not in fields and part not in match.positive:
                fields.append(part)
    return AskAgain(fields, [p for p in match.positive if p not in fields])


def _parse_prompt(at: str, raw: dict, module: str, groups: list, drills: bool, step: bool,
                  problems: list[str], schema=SCHEMA) -> Prompt | None:
    """One [[prompt]] (a question) or, with `step`, one [[step]] (a drill-only question)."""
    allowed = STEP_KEYS if step else PROMPT_KEYS + (STEP_TEXT_KEYS if drills else ())
    pid = raw.get("id")
    for key in raw:
        if key not in allowed:
            problems.append(f"{at}: unknown setting '{key}'. Allowed: {', '.join(allowed)}.")
    if not (isinstance(pid, str) and PROMPT_ID.match(pid)):
        problems.append(f"{at}: 'id' must use only lower-case letters, digits and hyphens.")
        return None
    if not step and raw.get("group") not in dict(groups):
        problems.append(f"{at}: 'group' must be one of the groups: {', '.join(k for k, _ in groups)}.")
    for key in ("question",) if step else ("question", "why"):
        if not _text(raw.get(key)):
            problems.append(f"{at}: '{key}' is missing.")
    for key in ("how_to_check", "why", "caution", "missing"):
        if key in raw and not _text(raw[key]):
            problems.append(f"{at}: '{key}' must be words when it is given.")
    if step and not _text(raw.get("missing")):
        problems.append(f"{at}: 'missing' must say, in the household's words, what is not recorded yet.")
    if "supply" in raw and not (isinstance(raw["supply"], str) and raw["supply"].count(".") == 1):
        problems.append(f"{at}: 'supply' must be a table with days of cover, like \"stock.items\".")
    every = raw.get("review_every", 12 if step else None)
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
    ask_again = None
    if "ask_again" in raw and schema != 3:
        problems.append(f"{at}: 'ask_again' needs schema = 3.")
    elif "ask_again" in raw and match is None:
        problems.append(f"{at}: 'ask_again' is only for a prompt with a match.")
    elif match is not None and "ask_again" in raw:
        ask_again = _check_ask_again(at, raw["ask_again"], match, problems)
    elif match is not None:
        if schema == 3:
            problems.append(f"{at}: a match needs 'ask_again', the fields whose change asks again, like "
                            f"{{ fields = [\"place\"] }}.")
        ask_again = _default_ask_again(match)
    write_in = raw.get("write_in")
    if write_in is not None and not (isinstance(write_in, dict) and set(write_in) == set(WRITE_IN_KEYS)
                                     and all(_text(v) for v in write_in.values())):
        problems.append(f"{at}: 'write_in' needs a table (module.table) and a label.")
        write_in = None
    source = {} if step else _check_source(at, raw.get("source"), problems)
    return Prompt(id=pid, group="" if step else str(raw.get("group")), question=str(raw.get("question", "")),
                  why=str(raw.get("why", "")), fits=_check_fits(at, raw.get("fits", {}), problems),
                  answered_by=str(answered_by), review_every=every if isinstance(every, int) else 12,
                  source=source, how_to_check=raw.get("how_to_check"), match=match, ask_again=ask_again,
                  write_in=write_in,
                  missing=raw.get("missing"), caution=raw.get("caution"), supply=raw.get("supply"))


def _parse_scenario(at: str, raw, known: set, problems: list[str]) -> Scenario | None:
    if not isinstance(raw, dict):
        problems.append(f"{at}: describe the scenario with id, version, title, intro, sources and steps.")
        return None
    for key in raw:
        if key not in SCENARIO_KEYS:
            problems.append(f"{at}: unknown setting '{key}'. Allowed: {', '.join(SCENARIO_KEYS)}.")
    sid = raw.get("id")
    if not (isinstance(sid, str) and PROMPT_ID.match(sid)):
        problems.append(f"{at}: 'id' must use only lower-case letters, digits and hyphens.")
        return None
    version = raw.get("version")
    if not (isinstance(version, int) and not isinstance(version, bool) and version >= 1):
        problems.append(f"{at}: 'version' must be a whole number from 1; raise it when the steps change.")
        version = 1
    for key in ("title", "intro"):
        if not _text(raw.get(key)):
            problems.append(f"{at}: '{key}' is missing.")
    sources = raw.get("sources")
    if not isinstance(sources, list) or not sources:
        problems.append(f"{at}: 'sources' must list at least one public source with the date it was checked.")
        sources = []
    sources = [s for s in (_scenario_source(at, s, problems) for s in sources) if s is not None]
    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) for s in steps):
        problems.append(f"{at}: 'steps' must list the questions in order, by id.")
        steps = []
    for step_id in steps:
        if step_id not in known:
            problems.append(f"{at}: step '{step_id}' is not a [[prompt]] or [[step]] in this file.")
    if len(set(steps)) != len(steps):
        problems.append(f"{at}: a step is listed twice.")
    every = raw.get("review_every", 12)
    if not (isinstance(every, int) and not isinstance(every, bool) and 1 <= every <= 60):
        problems.append(f"{at}: 'review_every' must be a number of months from 1 to 60.")
        every = 12
    return Scenario(id=sid, version=version, title=str(raw.get("title", "")), intro=str(raw.get("intro", "")),
                    fits=_check_fits(at, raw.get("fits", {}), problems, SCENARIO_FITS_KEYS), sources=sources,
                    steps=list(steps), review_every=every)


def _parse_emergency(where: str, raw_list, problems: list[str]) -> dict:
    """Emergency numbers, one per country, each from an official source. No number is presumed elsewhere."""
    found = {}
    for number, raw in enumerate(raw_list if isinstance(raw_list, list) else [], 1):
        at = f"{where}, emergency {number}"
        if not isinstance(raw, dict) or any(k not in EMERGENCY_KEYS for k in raw) or \
                not _text(raw.get("country")) or not (isinstance(raw.get("number"), str)
                                                      and re.fullmatch(r"\d{2,4}", raw["number"])):
            problems.append(f"{at}: say country, number (digits, as a word in quotes) and source.")
            continue
        if raw["country"] in found:
            problems.append(f"{at}: {raw['country']} already has an emergency number.")
        found[raw["country"]] = {"number": raw["number"], "source": _check_source(at, raw.get("source"), problems)}
    return found


def load(folder: Path, module: str, tables: dict, read_toml, problems: list[str]) -> PromptSet | None:
    """Read `prompts.toml` if the module has one. Every mistake is added to `problems` in plain words."""
    path = Path(folder) / FILE
    if not path.exists():
        return None
    data = read_toml(path, problems, required=False)
    if not data:
        return None
    where = f"In {FILE}"
    schema = data.get("schema")
    drills = schema in (2, 3)
    allowed = TOP_KEYS + (DRILL_KEYS if drills else ())
    for key in data:
        if key not in allowed:
            extra = " Drills need schema = 2 or 3." if key in DRILL_KEYS else ""
            problems.append(f"{where}: unknown setting '{key}'. Allowed: {', '.join(allowed)}.{extra}")
    if schema not in SCHEMAS:
        problems.append(f"{where}: 'schema' must be {', '.join(str(s) for s in SCHEMAS[:-1])} or {SCHEMAS[-1]}, "
                        f"the prompts formats "
                        f"this program reads.")
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
    prompts, steps, seen = [], [], set()
    for kind, raw_list, out in (("prompt", raw_prompts, prompts), ("step", data.get("step", []), steps)):
        for number, raw in enumerate(raw_list if isinstance(raw_list, list) else [], 1):
            pid = raw.get("id") if isinstance(raw, dict) else None
            at = f"{where}, {kind} {pid or number}"
            if not isinstance(raw, dict):
                problems.append(f"{at}: describe the {kind} with id, question and what may answer it.")
                continue
            parsed = _parse_prompt(at, raw, module, groups, drills, kind == "step", problems,
                                   schema if schema in SCHEMAS else SCHEMA)
            if parsed is None:
                continue
            if parsed.id in seen:
                problems.append(f"{at}: another prompt already has this id (prompts and steps share ids).")
            seen.add(parsed.id)
            out.append(parsed)
    scenarios = []
    for number, raw in enumerate(data.get("scenario", []) if isinstance(data.get("scenario", []), list) else [], 1):
        sid = raw.get("id") if isinstance(raw, dict) else None
        scenario = _parse_scenario(f"{where}, scenario {sid or number}", raw, seen, problems)
        if scenario is not None:
            if any(s.id == scenario.id for s in scenarios):
                problems.append(f"{where}, scenario {scenario.id}: another scenario already has this id.")
            scenarios.append(scenario)
    runs_ok = True
    if drills and (scenarios or "runs" in data or "run_steps" in data):
        runs_ok = _check_run_tables(where, data, tables, problems)
    if not answers_ok or not runs_ok:
        return None
    return PromptSet(module=module, answers=data["answers"], groups=groups, prompts=prompts,
                     runs=data.get("runs") if scenarios else None,
                     run_steps=data.get("run_steps") if scenarios else None, scenarios=scenarios, steps=steps,
                     emergency=_parse_emergency(where, data.get("emergency", []), problems) if drills else {})


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
    """Check each match, supply and has_records against the tables it names, once those modules are loaded.

    A match into a module that is not installed is fine: it simply finds nothing (decision 0104)."""
    problems = []
    for prompt in prompt_set.prompts + prompt_set.steps:
        where = f"In {FILE}, {'prompt' if prompt.group else 'step'} {prompt.id}"
        if prompt.supply:
            mod, _, tname = prompt.supply.partition(".")
            table = by_name[mod].tables.get(tname) if mod in by_name else None
            if mod in by_name and (table is None or not table.watch.get("supply")):
                problems.append(f"{where}: supply '{prompt.supply}' is not a table with days of cover.")
        if prompt.match is None:
            continue
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

        ask = prompt.ask_again or AskAgain()
        for path in list(prompt.match.where) + prompt.match.filled + prompt.match.positive + ask.fields:
            first = table.columns.get(path.split(".")[0])
            if first is not None and "." in path and first.type == "link" and tables_of(first) is None:
                continue  # the link leads to a module that is not installed: the match finds nothing
            column = _column_at(path, table, tables_of)
            if column is None:
                problems.append(f"{where}: '{path}' is not a field of '{prompt.match.table}'.")
            elif column.type == "links":
                problems.append(f"{where}: '{path}' links several records, so it cannot be in ask_again.")
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
    for scenario in prompt_set.scenarios:
        wanted = scenario.fits.get("has_records")
        if wanted:
            mod, _, tname = wanted.partition(".")
            if mod in by_name and tname not in by_name[mod].tables:
                problems.append(f"In {FILE}, scenario {scenario.id}: has_records '{wanted}' is not a table.")
    return problems
