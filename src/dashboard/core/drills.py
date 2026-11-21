"""Think it through: which drills fit the household, what each step may find in its records, and the practice runs kept with their dates.

Decision 0108, built on decision 0104's questions. A drill (a `[[scenario]]` in a module's prompts.toml) is
an ordered run of steps. A step is a drill-only `[[step]]` or a shared `[[prompt]]`; answering a shared one
here also saves the household's ordinary answer on the Questions page. Each run is a record in the module's
runs table and each step's choice a record in its run_steps table, written through Records like any other,
so history and backups cover them. A person's own words are a private column that never travels, exports
or reaches a helper. Nothing here answers for the household or says that it is safe or ready.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

from dashboard.core import dates, questions, watch
from dashboard.core.prompts import STEP_CHOICES, Prompt, PromptSet, Scenario
from dashboard.core.records import Records, RecordNotFound, TableInfo, ValidationError
from dashboard.core.schema import table_name

CHOICE_WORDS = {"plan": "I have a plan", "check": "I need to check", "not_relevant": "Not relevant to my household"}
# A shared step's choice becomes the same ordinary answer on the Questions page. Own words never go with it.
TO_ANSWER = {"plan": "yes", "check": "not_yet", "not_relevant": "not_relevant"}
SOURCE_FRESH_MONTHS = 12  # a drill source checked longer ago than this shows "Source needs checking"
LOCAL_NUMBER = "Use your local emergency number"


@dataclass
class Drill:
    """One drill with where it stands for this household today."""
    module: str
    scenario: Scenario
    reasons: list = field(default_factory=list)   # why it does not fit the settings; empty when it fits
    runs: list = field(default_factory=list)      # the household's runs, newest first
    changed: bool = False                         # a record chosen in the latest practice changed since

    @property
    def fits(self) -> bool:
        return not self.reasons

    @property
    def practised(self) -> dict | None:
        return next((r for r in self.runs if r["status"] == "practised"), None)

    @property
    def in_progress(self) -> dict | None:
        return next((r for r in self.runs if r["status"] == "in_progress"), None)

    def due(self, today: date) -> bool:
        last = self.practised
        return bool(last and last.get("review_on") and str(last["review_on"])[:10] <= today.isoformat())


def drill_sets(registry: dict[str, TableInfo]) -> dict[str, PromptSet]:
    """The modules switched on whose prompts.toml has drills and whose run tables are on, by module name."""
    found = {}
    for prompt_set in questions.prompt_sets(registry).values():
        if prompt_set.scenarios and runs_table(prompt_set) in registry and steps_table(prompt_set) in registry:
            found[prompt_set.module] = prompt_set
    return found


def runs_table(prompt_set: PromptSet) -> str:
    return table_name(prompt_set.module, prompt_set.runs or "")


def steps_table(prompt_set: PromptSet) -> str:
    return table_name(prompt_set.module, prompt_set.run_steps or "")


# ----- what fits, what is cited -------------------------------------------------------------------

def scenario_fits(conn: sqlite3.Connection, registry: dict[str, TableInfo], scenario: Scenario, home: dict,
                  hazard_names: dict | None = None) -> list[str]:
    """Why a drill does not fit, from the household's Settings and, for has_records, whether it keeps any
    record in that table (a vehicle for a breakdown drill). Never a guess from an address."""
    rule = {k: v for k, v in scenario.fits.items() if k != "has_records"}
    reasons = questions.fits_rule(rule, home, hazard_names)
    wanted = scenario.fits.get("has_records")
    if wanted:
        module, _, name = wanted.partition(".")
        info = registry.get(table_name(module, name))
        if info is None:
            reasons.append("The list it needs is switched off in Settings.")
        elif not conn.execute(f"SELECT 1 FROM {info.name} WHERE deleted_at IS NULL LIMIT 1").fetchone():
            reasons.append(f"Nothing is recorded in {info.table.title} yet.")
    return reasons


def sources(scenario: Scenario, country: str, today: date) -> list[dict]:
    """The drill's sources for this household. One limited to some countries is shown only where Settings
    name one of them, so (say) UK motorway advice never reaches an Australian household. A broken or old
    source is kept and marked, never dropped or replaced (Lane B's check 12)."""
    shown = []
    for source in scenario.sources:
        if source.get("country") and country not in source["country"]:
            continue
        stale = source["broken"] or source["checked"] > today.isoformat() or \
            dates.add_period(source["checked"], SOURCE_FRESH_MONTHS, "months") < today.isoformat()
        shown.append({**source, "needs_checking": stale})
    return shown


def emergency(prompt_set: PromptSet, country: str) -> dict | None:
    """The checked emergency number for the household's country, with its source; None anywhere else."""
    return prompt_set.emergency.get(country) if country else None


def fitting_steps(prompt_set: PromptSet, scenario: Scenario, home: dict, hazard_names: dict | None = None
                  ) -> list[Prompt]:
    """The drill's steps that fit the household's settings, in order (a building's own fire plan, say, is
    asked of a flat, not a house)."""
    out = []
    for step_id in scenario.steps:
        step = prompt_set.step(step_id)
        if step is not None and not questions.fits_rule(step.fits, home, hazard_names):
            out.append(step)
    return out


def supply(conn: sqlite3.Connection, registry: dict[str, TableInfo], step: Prompt) -> watch.Supply | None:
    """The days-of-cover working a step points at, only when it can really be worked out; else None."""
    if not step.supply:
        return None
    name = table_name(*step.supply.split(".", 1))
    found = next((s for s in watch.supplies(conn, registry) if s.table == name), None)
    if found is None or found.needs_household or found.total <= 0 or found.days is None:
        return None
    return found


# ----- runs -------------------------------------------------------------------------------------------

def list_runs(conn: sqlite3.Connection, prompt_set: PromptSet, scenario_id: str) -> list[dict]:
    """Every run of one drill, newest first. Earlier runs are kept, never overwritten."""
    return [dict(r) for r in conn.execute(
        f"SELECT * FROM {runs_table(prompt_set)} WHERE deleted_at IS NULL AND scenario = ? "
        f"ORDER BY COALESCE(practised_on, started_on) DESC, id DESC", (scenario_id,))]


def run_answers(conn: sqlite3.Connection, prompt_set: PromptSet, run_id: int) -> dict[str, dict]:
    """A run's step answers by step ID. The own-words column is read only to say whether any were saved."""
    found = {}
    for row in conn.execute(f"SELECT * FROM {steps_table(prompt_set)} WHERE deleted_at IS NULL AND run = ? "
                            f"ORDER BY id", (run_id,)):
        row = dict(row)
        row["has_words"] = bool((row.pop("own_words", None) or "").strip())
        found[row["step"]] = row
    return found


def record_changed(conn: sqlite3.Connection, registry: dict[str, TableInfo], prompt_set: PromptSet,
                   answer: dict) -> bool:
    """True when the record chosen at a step changed, moved, was deleted or stopped matching since."""
    step = prompt_set.step(answer["step"])
    if not answer.get("record") or step is None:
        return False
    same = [c for c in questions.candidates(conn, registry, step) if c.key == answer["record"]]
    return not same or same[0].check != answer.get("record_check")


def overview(conn: sqlite3.Connection, registry: dict[str, TableInfo], prompt_set: PromptSet,
             hazard_names: dict | None = None) -> list[Drill]:
    """Every drill of one module with what fits and the household's runs, in the order written."""
    home, out = questions.profile(conn, registry), []
    for scenario in prompt_set.scenarios:
        drill = Drill(prompt_set.module, scenario, scenario_fits(conn, registry, scenario, home, hazard_names),
                      list_runs(conn, prompt_set, scenario.id))
        last = drill.practised
        if last is not None:
            drill.changed = any(record_changed(conn, registry, prompt_set, a)
                                for a in run_answers(conn, prompt_set, last["id"]).values())
        out.append(drill)
    return out


def _run(store: Records, prompt_set: PromptSet, run_id: int) -> dict:
    try:
        return store.get(runs_table(prompt_set), int(run_id))
    except (RecordNotFound, ValueError, TypeError):
        raise ValidationError({"run": "that practice run is not here any more."}) from None


def start(store: Records, prompt_set: PromptSet, scenario_id: str, today: date | None = None,
          actor: str = "person") -> int:
    """Begin a practice run, or carry on with one already started. Nothing is marked practised."""
    scenario = prompt_set.scenario(scenario_id)
    if scenario is None:
        raise ValidationError({"scenario": "is not one of the drills."})
    open_run = next((r for r in list_runs(store.conn, prompt_set, scenario_id) if r["status"] == "in_progress"),
                    None)
    if open_run is not None:
        return open_run["id"]
    today = today or date.today()
    return store.create(runs_table(prompt_set), {"scenario": scenario.id, "scenario_version": scenario.version,
                                                 "started_on": today.isoformat(), "status": "in_progress"},
                        actor=actor)


def save_step(store: Records, prompt_set: PromptSet, run_id: int, step_id: str, choice: str,
              own_words: str | None = None, record: str | None = None, today: date | None = None,
              actor: str = "person") -> int:
    """Save a person's choice at one step of a run still in progress; return the step answer's id.

    Own words, if typed, replace earlier ones; left blank, earlier ones are kept. A record is kept only when
    it is one the step offers right now. A shared step also saves the ordinary answer on the Questions page
    (plan = Yes, check = Not yet, not relevant = Not relevant), never with the person's own words."""
    today = today or date.today()
    run = _run(store, prompt_set, run_id)
    scenario = prompt_set.scenario(run["scenario"])
    if run["status"] != "in_progress" or scenario is None:
        raise ValidationError({"run": "this practice is finished; start a new one to answer again."})
    if step_id not in scenario.steps:
        raise ValidationError({"step": "is not a step of this drill."})
    if choice not in STEP_CHOICES:
        raise ValidationError({"choice": "choose I have a plan, I need to check, or Not relevant."})
    step = prompt_set.step(step_id)
    chosen = None
    if record:
        offered = {c.key: c for c in questions.candidates(store.conn, store.registry, step)}
        if record not in offered:
            raise ValidationError({"record": "that record cannot be used for this step. Choose again."})
        chosen = offered[record]
    values = {"run": run["id"], "step": step_id, "choice": choice,
              "record": chosen.key if chosen else None, "record_check": chosen.check if chosen else None}
    if own_words and own_words.strip():
        values["own_words"] = own_words.strip()
    existing = run_answers(store.conn, prompt_set, run["id"]).get(step_id)
    table = steps_table(prompt_set)
    if existing is not None:
        store.update(table, existing["id"], values, actor=actor)
        answer_id = existing["id"]
    else:
        answer_id = store.create(table, values, actor=actor)
    if prompt_set.is_shared(step_id):
        questions.save(store, prompt_set, step_id, TO_ANSWER[choice],
                       record=chosen.key if chosen and choice == "plan" else None, today=today, actor=actor)
    return answer_id


def suggested_review(scenario: Scenario, practised_on: str) -> str:
    """The look-again date offered: an editorial suggestion, not an official deadline."""
    return dates.add_period(practised_on, scenario.review_every, "months")


def finish(store: Records, prompt_set: PromptSet, run_id: int, step_ids: list[str], practised_on: str,
           review_on: str | None, today: date | None = None, actor: str = "person") -> None:
    """Mark a run practised on the date given, with the look-again date the household chose. Every step
    that fits must have a choice first; a run left part-way stays "Continue later" with no practised date."""
    today = today or date.today()
    run = _run(store, prompt_set, run_id)
    scenario = prompt_set.scenario(run["scenario"])
    if run["status"] != "in_progress" or scenario is None:
        raise ValidationError({"run": "this practice is already saved."})
    answered = run_answers(store.conn, prompt_set, run["id"])
    if any(s not in answered for s in step_ids):
        raise ValidationError({"steps": "answer every step first, or choose Continue later."})
    if practised_on > today.isoformat():
        raise ValidationError({"practised_on": "choose today or an earlier date."})
    review_on = review_on or suggested_review(scenario, practised_on)
    if review_on < practised_on:
        raise ValidationError({"review_on": "choose a date on or after the practice."})
    store.update(runs_table(prompt_set), run["id"], {"status": "practised", "practised_on": practised_on,
                                                     "review_on": review_on}, actor=actor)
