"""The "Have you thought about…?" screens: the questions by group, one question with its four answers, and Not now."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from dashboard.core import dates, drills, questions, records
from dashboard.core.records import ValidationError
from dashboard.web import display
from dashboard.web.setup import HAZARDS

question_pages = Blueprint("questions", __name__)
FILTERS = {"to_look_at": "To look at", "looked_at": "Looked at", "review": "Review again",
           "not_relevant": "Not relevant", "does_not_fit": "Does not fit settings"}
ANSWER_WORDS = {"yes": "Yes", "not_relevant": "Not relevant", "not_yet": "Not yet"}
# The same words wherever a question comes back; they never repeat what a record says.
REVIEW_WORDS = {"record_changed": "The record you used for this answer changed. Does your answer still fit?",
                "record_missing": "The record you used for this answer is no longer available. Does your answer "
                                  "still fit?",
                "due": "It is time to look at your answer again. Does it still fit?"}


def _registry():
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), _registry())


def _today() -> date:
    return current_app.config.get("TODAY", date.today)()


def _set(module: str):
    found = questions.prompt_sets(_registry()).get(module)
    if found is None:
        abort(404)
    return found


def _evaluate(prompt_set):
    return questions.evaluate(current_app.config["CONNECT"](), _registry(), prompt_set, _today(), dict(HAZARDS))


def in_filter(q: questions.Question, show: str) -> bool:
    if show == "not_relevant":
        return q.state == "looked_at" and q.answer["answer"] == "not_relevant"
    return q.state == show


def candidate_view(store: records.Records, q: questions.Question, formatter) -> list[dict]:
    """What a person sees of each record that may answer a question. A private one shows only that it exists."""
    out = []
    for c in q.candidates:
        info = store.registry[c.table]
        link = url_for("pages.edit_record", table=c.table, record_id=c.record_id)
        if c.private:
            out.append({"key": c.key, "private": True, "link": link})
            continue
        parts = []
        if info.table.record_name or (display.name_column(info) and display.name_column(info).required):
            parts.append(display.display_name(info, c.row, store))
        match = q.prompt.match
        for path in list(match.where) + match.filled + match.positive:
            first, _, rest = path.partition(".")
            column = info.table.columns[first]
            if column.sensitive or c.row.get(first) in (None, ""):
                continue
            text = formatter.text(info, column, c.row.get(first))
            words = [f"{display.column_label(info, column)}: {text}"]
            if rest:
                target = formatter.target(info, column)
                inner = target.table.columns[rest]
                linked = store.get(target.name, int(c.row[first]))
                if not inner.sensitive and linked.get(rest) not in (None, ""):
                    words.append(f"{display.column_label(target, inner)}: "
                                 f"{formatter.text(target, inner, linked.get(rest))}")
            parts.extend(w for w in words if not any(w.split(": ", 1)[-1] == p for p in parts))
        out.append({"key": c.key, "private": False, "link": link, "text": " · ".join(dict.fromkeys(parts))})
    return out


def _history(store: records.Records, prompt_set, answer: dict | None, style: str) -> list[dict]:
    if answer is None:
        return []
    out = []
    for entry in reversed(store.history(questions.answers_table(prompt_set), answer["id"])):
        after = entry["after"] or {}
        if "answer" not in after and "answered_on" not in after:
            continue
        before = entry["before"] or {}
        merged = {**before, **after}
        out.append({"at": dates.show(str(merged.get("answered_on") or entry["at"])[:10], style), "who": display.actor_text(entry["actor"]),
                    "answer": ANSWER_WORDS.get(merged.get("answer"), ""),
                    "record": bool(merged.get("record"))})
    return out


@question_pages.get("/questions")
def all_questions():
    sets = questions.prompt_sets(_registry())
    if not sets:
        abort(404)
    return redirect(url_for("questions.question_list", module=sorted(sets)[0]))


@question_pages.get("/questions/<module>")
def question_list(module):
    prompt_set = _set(module)
    found = _evaluate(prompt_set)
    show = request.args.get("show", "")
    show = show if show in FILTERS else ""
    counts = {key: sum(1 for q in found if in_filter(q, key)) for key in FILTERS}
    style = dates.household_style(current_app.config["CONNECT"]())
    groups = []
    for key, title in prompt_set.groups:
        items = [q for q in found if q.prompt.group == key and (not show or in_filter(q, show))]
        groups.append({"key": key, "title": title, "questions": items})
    return render_template("questions.html", module=module, title=_title(module), groups=groups,
                           coverage=questions.coverage(found, prompt_set), filters=FILTERS, show=show,
                           counts=counts, answer_words=ANSWER_WORDS, style=style, show_date=dates.show,
                           drills_link=url_for("drills.drill_list", module=module) if prompt_set.scenarios
                           and module in drills.drill_sets(_registry()) else None)


def _title(module: str) -> str:
    info = next(i for i in _registry().values() if i.module.name == module)
    return info.module.title


def _render_question(module: str, prompt_id: str, errors: dict | None = None, values: dict | None = None,
                     status: int = 200):
    prompt_set = _set(module)
    q = next((x for x in _evaluate(prompt_set) if x.prompt.id == prompt_id), None)
    if q is None:
        abort(404)
    store = _store()
    style = dates.household_style(store.conn)
    formatter = display.Formatter(store)
    write_in = None
    if q.prompt.write_in:
        other, _, name = q.prompt.write_in["table"].partition(".")
        table = f"{other}__{name}"
        if table in store.registry:
            write_in = {"href": url_for("pages.new_record", table=table), "label": q.prompt.write_in["label"]}
    default_review = values.get("review_on") if values else None
    if default_review is None:
        suggested = dates.add_period(_today(), q.prompt.review_every, "months")
        default_review = dates.show(suggested, style)
    return render_template(
        "question.html", module=module, title=_title(module), q=q, group=prompt_set.group_title(q.prompt.group),
        candidates=candidate_view(store, q, formatter), write_in=write_in, errors=errors or {},
        values=values or {}, review_value=default_review, date_hint=dates.HINTS[style],
        answer_words=ANSWER_WORDS, review_words=REVIEW_WORDS, show_date=lambda v: dates.show(v, style),
        history=_history(store, prompt_set, q.answer, style), saved=request.args.get("saved") == "1",
        interval=q.prompt.review_every), status


@question_pages.get("/questions/<module>/<prompt_id>")
def question_page(module, prompt_id):
    return _render_question(module, prompt_id)


@question_pages.post("/questions/<module>/<prompt_id>")
def answer_question(module, prompt_id):
    prompt_set = _set(module)
    if prompt_set.get(prompt_id) is None:
        abort(404)
    store = _store()
    form = request.form
    typed = form.get("review_on", "").strip()
    values = {"review_on": typed, "note": form.get("note", ""), "record": form.get("record", "")}
    review_on = None
    if typed:
        try:
            review_on = dates.parse(typed, dates.household_style(store.conn))
        except ValueError as error:
            return _render_question(module, prompt_id, {"review_on": str(error)}, values, 422)
        if review_on < _today().isoformat():
            return _render_question(module, prompt_id, {"review_on": "Choose today or a later date."}, values, 422)
    try:
        questions.save(store, prompt_set, prompt_id, form.get("answer", ""), review_on, form.get("note"),
                       form.get("record") or None, _today())
    except ValidationError as error:
        return _render_question(module, prompt_id, error.problems, values, 422)
    return redirect(url_for("questions.question_page", module=module, prompt_id=prompt_id, saved="1"))


@question_pages.post("/questions/<module>/<prompt_id>/not-now")
def set_aside(module, prompt_id):
    prompt_set = _set(module)
    if prompt_set.get(prompt_id) is None:
        abort(404)
    questions.not_now(current_app.config["CONNECT"](), f"{module}:{prompt_id}", _today())
    back = request.form.get("back", "/")
    return redirect(back if back in ("/", "/attention") else "/")
