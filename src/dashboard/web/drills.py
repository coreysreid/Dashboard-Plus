"""The "Think it through" screens: the drills that fit, one drill's sources and steps, each step with its records, and saving a practice."""
from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from dashboard.core import dates, drills, questions, records
from dashboard.core.records import ValidationError
from dashboard.web import display
from dashboard.web.questions import ANSWER_WORDS, candidate_view
from dashboard.web.setup import HAZARDS

drill_pages = Blueprint("drills", __name__)
# The same words wherever a chosen record changed; they never repeat what the record says.
CHANGED_WORDS = "A record you chose for this practice changed since. Look at this step again when you have time."


def _registry():
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), _registry())


def _today() -> date:
    return current_app.config.get("TODAY", date.today)()


def _set(module: str):
    found = drills.drill_sets(_registry()).get(module)
    if found is None:
        abort(404)
    return found


def _scenario(prompt_set, scenario_id: str):
    scenario = prompt_set.scenario(scenario_id)
    if scenario is None:
        abort(404)
    return scenario


def _home():
    return questions.profile(current_app.config["CONNECT"](), _registry())


def _common(prompt_set, scenario=None) -> dict:
    """What every drill page shows: the emergency line for the household's country and the date style."""
    home = _home()
    style = dates.household_style(current_app.config["CONNECT"]())
    found = drills.emergency(prompt_set, home["country"])
    out = {"module": prompt_set.module, "emergency": found, "local_number": drills.LOCAL_NUMBER,
           "show_date": lambda v: dates.show(v, style) if v else "", "style": style}
    if scenario is not None:
        out["scenario"] = scenario
        out["sources"] = drills.sources(scenario, home["country"], _today())
    return out


def _run(prompt_set, scenario, run_id: int) -> dict:
    try:
        run = _store().get(drills.runs_table(prompt_set), run_id)
    except records.RecordNotFound:
        abort(404)
    if run["scenario"] != scenario.id:
        abort(404)
    return run


def _steps(prompt_set, scenario):
    return drills.fitting_steps(prompt_set, scenario, _home(), dict(HAZARDS))


@drill_pages.get("/drills")
def all_drills():
    sets = drills.drill_sets(_registry())
    if not sets:
        abort(404)
    return redirect(url_for("drills.drill_list", module=sorted(sets)[0]))


@drill_pages.get("/drills/<module>")
def drill_list(module):
    prompt_set = _set(module)
    found = drills.overview(current_app.config["CONNECT"](), _registry(), prompt_set, dict(HAZARDS))
    return render_template("drills.html", fitting=[d for d in found if d.fits],
                           not_fitting=[d for d in found if not d.fits], today=_today(),
                           changed_words=CHANGED_WORDS, **_common(prompt_set))


@drill_pages.get("/drills/<module>/<scenario_id>")
def drill_page(module, scenario_id):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    conn = current_app.config["CONNECT"]()
    drill = next(d for d in drills.overview(conn, _registry(), prompt_set, dict(HAZARDS))
                 if d.scenario.id == scenario.id)
    runs = []
    for run in drill.runs:
        answers = drills.run_answers(conn, prompt_set, run["id"])
        runs.append({**run, "answered": len(answers),
                     "changed": any(drills.record_changed(conn, _registry(), prompt_set, a) for a in answers.values())})
    return render_template("drill.html", drill=drill, steps=_steps(prompt_set, scenario), runs=runs,
                           today=_today(), saved=request.args.get("saved"), changed_words=CHANGED_WORDS,
                           **_common(prompt_set, scenario))


@drill_pages.post("/drills/<module>/<scenario_id>/start")
def start(module, scenario_id):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    run_id = drills.start(_store(), prompt_set, scenario.id, _today())
    answered = drills.run_answers(current_app.config["CONNECT"](), prompt_set, run_id)
    steps = _steps(prompt_set, scenario)
    number = next((n for n, s in enumerate(steps, 1) if s.id not in answered), None)
    if number is None:
        return redirect(url_for("drills.run_page", module=module, scenario_id=scenario.id, run_id=run_id))
    return redirect(url_for("drills.step_page", module=module, scenario_id=scenario.id, run_id=run_id,
                            number=number))


def _add_link(store, step) -> dict | None:
    """Where to add the missing record, with the match's simple values filled in (a water shut-off)."""
    if step.match is None:
        return None
    module, _, name = step.match.table.partition(".")
    table = f"{module}__{name}"
    if table not in store.registry:
        return None
    info = store.registry[table]
    prefill = {}
    for path, value in step.match.where.items():
        column = info.table.columns.get(path)
        if column is None or "." in path or isinstance(value, list):
            continue
        prefill[path] = ("yes" if value else "") if column.type == "boolean" else value
    href = url_for("pages.new_record", table=table)
    return {"href": href + ("?" + urlencode(prefill) if prefill else ""), "title": display.table_title(info)}


def _render_step(prompt_set, scenario, run, number: int, errors: dict | None = None, values: dict | None = None,
                 status: int = 200):
    steps = _steps(prompt_set, scenario)
    if not 1 <= number <= len(steps):
        abort(404)
    step = steps[number - 1]
    store = _store()
    q = questions.Question(prompt_set.module, step, True)
    q.candidates = questions.candidates(store.conn, store.registry, step)
    answers = drills.run_answers(store.conn, prompt_set, run["id"])
    saved = answers.get(step.id)
    supply = drills.supply(store.conn, store.registry, step)
    shared = questions.current_answers(store.conn, prompt_set).get(step.id) if prompt_set.is_shared(step.id) \
        else None
    return render_template(
        "drill_step.html", run=run, step=step, number=number, total=len(steps),
        shared=prompt_set.is_shared(step.id), shared_answer=shared, answer_words=ANSWER_WORDS,
        candidates=candidate_view(store, q, display.Formatter(store)), add=_add_link(store, step),
        supply=supply, saved=saved, changed=bool(saved and drills.record_changed(
            store.conn, store.registry, prompt_set, saved)), changed_words=CHANGED_WORDS,
        steps_table=drills.steps_table(prompt_set), choice_words=drills.CHOICE_WORDS,
        errors=errors or {}, values=values or {}, **_common(prompt_set, scenario)), status


@drill_pages.get("/drills/<module>/<scenario_id>/runs/<int:run_id>/<int:number>")
def step_page(module, scenario_id, run_id, number):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    run = _run(prompt_set, scenario, run_id)
    if run["status"] != "in_progress":
        return redirect(url_for("drills.run_page", module=module, scenario_id=scenario.id, run_id=run_id))
    return _render_step(prompt_set, scenario, run, number)


@drill_pages.post("/drills/<module>/<scenario_id>/runs/<int:run_id>/<int:number>")
def save_step(module, scenario_id, run_id, number):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    run = _run(prompt_set, scenario, run_id)
    steps = _steps(prompt_set, scenario)
    if not 1 <= number <= len(steps):
        abort(404)
    form = request.form
    values = {"choice": form.get("choice", ""), "record": form.get("record", "")}
    try:
        drills.save_step(_store(), prompt_set, run_id, steps[number - 1].id, values["choice"],
                         form.get("own_words"), values["record"] or None, _today())
    except ValidationError as error:
        if run["status"] != "in_progress":
            abort(409)
        return _render_step(prompt_set, scenario, run, number, error.problems, values, 422)
    if form.get("action") == "later":
        return redirect(url_for("drills.drill_page", module=module, scenario_id=scenario.id, saved="later"))
    if number < len(steps):
        return redirect(url_for("drills.step_page", module=module, scenario_id=scenario.id, run_id=run_id,
                                number=number + 1))
    return redirect(url_for("drills.run_page", module=module, scenario_id=scenario.id, run_id=run_id))


def _render_run(prompt_set, scenario, run, errors: dict | None = None, values: dict | None = None,
                status: int = 200):
    store = _store()
    answers = drills.run_answers(store.conn, prompt_set, run["id"])
    style = dates.household_style(store.conn)
    rows = []
    for number, step in enumerate(_steps(prompt_set, scenario), 1):
        answer = answers.get(step.id)
        rows.append({"number": number, "step": step, "answer": answer,
                     "changed": bool(answer and drills.record_changed(store.conn, store.registry, prompt_set,
                                                                     answer))})
    complete = all(r["answer"] for r in rows)
    practised = (values or {}).get("practised_on") or dates.show(_today().isoformat(), style)
    review = (values or {}).get("review_on") or dates.show(
        drills.suggested_review(scenario, _today().isoformat()), style)
    return render_template("drill_run.html", run=run, rows=rows, complete=complete, errors=errors or {},
                           practised_value=practised, review_value=review, date_hint=dates.HINTS[style],
                           steps_table=drills.steps_table(prompt_set), choice_words=drills.CHOICE_WORDS,
                           changed_words=CHANGED_WORDS, saved=request.args.get("saved") == "1",
                           **_common(prompt_set, scenario)), status


@drill_pages.get("/drills/<module>/<scenario_id>/runs/<int:run_id>")
def run_page(module, scenario_id, run_id):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    return _render_run(prompt_set, scenario, _run(prompt_set, scenario, run_id))


@drill_pages.post("/drills/<module>/<scenario_id>/runs/<int:run_id>/finish")
def finish(module, scenario_id, run_id):
    prompt_set = _set(module)
    scenario = _scenario(prompt_set, scenario_id)
    run = _run(prompt_set, scenario, run_id)
    store = _store()
    style = dates.household_style(store.conn)
    values = {"practised_on": request.form.get("practised_on", "").strip(),
              "review_on": request.form.get("review_on", "").strip()}
    parsed = {}
    for name in values:
        if not values[name]:
            continue
        try:
            parsed[name] = dates.parse(values[name], style)
        except ValueError as error:
            return _render_run(prompt_set, scenario, run, {name: str(error)}, values, 422)
    try:
        drills.finish(store, prompt_set, run_id, [s.id for s in _steps(prompt_set, scenario)],
                      parsed.get("practised_on") or _today().isoformat(), parsed.get("review_on"), _today())
    except ValidationError as error:
        return _render_run(prompt_set, scenario, run, error.problems, values, 422)
    return redirect(url_for("drills.run_page", module=module, scenario_id=scenario.id, run_id=run_id, saved="1"))
