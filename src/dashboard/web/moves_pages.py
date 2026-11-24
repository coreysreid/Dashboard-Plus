"""One reminder per policy (decision 0117): the household's choice screen, Review and move row by row, Transfer back, and the notices on each record's page."""
from __future__ import annotations

from datetime import date
from urllib.parse import quote

from flask import Blueprint, abort, current_app, redirect, render_template, request
from markupsafe import Markup, escape

from dashboard.core import backups, dates, records, reminder_moves
from dashboard.errors import PlainError
from dashboard.web import display

moves_pages = Blueprint("moves", __name__)


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _rules(store) -> list[reminder_moves.Rule]:
    return reminder_moves.rules(store.registry, current_app.config.get("LOADED") or [])


def _date_words(store, value) -> str | None:
    try:
        return dates.show(date.fromisoformat(str(value)[:10]), dates.household_style(store.conn))
    except ValueError:
        return None


def _with_link(text: str, name: str, href: str | None) -> Markup:
    """The sentence with the record's name as a link to it, everything else escaped."""
    if not href or not name or name not in text:
        return escape(text)
    before, _, after = text.partition(name)
    return escape(before) + Markup(f'<a href="{escape(href)}">{escape(name)}</a>') + escape(after)


def _row(store, table: str, record_id) -> dict | None:
    if record_id is None:
        return None
    row = store.conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
    return dict(row) if row else None


def choice_box(store, info) -> dict | None:
    """The first-time screen on the newer list (Bills): older records still remind and nobody has chosen yet."""
    rule = next((r for r in _rules(store) if r.target.name == info.name and r.target_on), None)
    if rule is None or not reminder_moves.show_choice(store.conn, rule):
        return None
    count = sum(1 for c in reminder_moves.candidates(store.conn, store.registry, rule) if c["state"] is None)
    return {"target": rule.target.name, "title": reminder_moves.words(rule, "title"),
            "intro": reminder_moves.words(rule, "intro", count=count),
            "keep": reminder_moves.words(rule, "keep"), "review": reminder_moves.words(rule, "review"),
            "later": reminder_moves.words(rule, "later"), "later_chosen": reminder_moves.choice(store.conn, rule)}


def review_link(store, info) -> dict | None:
    """Once the household has chosen, a quiet link back to Review and move, so the choice can be changed."""
    rule = next((r for r in _rules(store) if r.target.name == info.name and r.target_on), None)
    if rule is None or rule.source is None or reminder_moves.show_choice(store.conn, rule) or \
            not reminder_moves.candidates(store.conn, store.registry, rule):
        return None
    return {"href": f"/moves/{rule.target.name}", "label": reminder_moves.words(rule, "review")}


def record_notices(store, info, record: dict, moved: bool = False) -> list[dict]:
    """What a record's page says about where its reminder is, with Transfer back or Move here again. `moved`: the
    page was opened straight after a move, so it says the move is done."""
    if not record or record.get("deleted_at"):
        return []
    found = []
    for rule in _rules(store):
        if rule.source_name == info.name:
            move = reminder_moves.entry(store.conn, info.name, record["id"])
            back = {"action": f"/moves/{rule.target.name}/{record['id']}/back",
                    "label": reminder_moves.words(rule, "back")}
            if move and move["state"] == reminder_moves.MOVED:
                target = _row(store, rule.target.name, move["target_id"])
                name = str((target or {}).get("name") or "")
                if rule.target_on:
                    text = reminder_moves.words(rule, "source_moved", name=name)
                    href = f"/t/{rule.target.name}/{move['target_id']}"
                    if target is not None and target.get("deleted_at"):
                        text += " That record is deleted; restore it there, or choose Transfer back."
                    found.append({"words": _with_link(text, name, href), "forms": [back], "key": "source_moved"})
                else:
                    found.append({"words": escape(reminder_moves.words(rule, "target_off")), "forms": [back],
                                  "key": "target_off"})
            elif rule.target_on:
                when = _date_words(store, record.get(rule.source_date))
                text = (reminder_moves.words(rule, "source_kept", date=when) if when else
                        reminder_moves.words(rule, "no_date"))
                forms = [] if move else [{"href": f"/moves/{rule.target.name}",
                                          "label": reminder_moves.words(rule, "review")}]
                found.append({"words": escape(text), "forms": forms, "key": "source_kept"})
        elif rule.target.name == info.name and rule.target_on:
            move = reminder_moves.entry(store.conn, info.name, record["id"])
            if not move or move["target_id"] != record["id"]:
                continue
            source = _row(store, rule.source_name, move["source_id"])
            earlier = None
            if rule.source is not None and source is not None and not source.get("deleted_at"):
                earlier = {"href": f"/t/{rule.source_name}/{move['source_id']}",
                           "label": f"Earlier {rule.source.table.title} record"}
            if move["state"] == reminder_moves.MOVED:
                if moved:
                    found.append({"words": escape(reminder_moves.words(rule, "moved", name=str(record.get("name") or
                                                                                              ""))),
                                  "forms": [], "key": "moved"})
                when = _date_words(store, record.get(rule.date))
                text = (reminder_moves.words(rule, "target_moved", date=when) if when else
                        reminder_moves.words(rule, "no_date"))
                forms = [{"action": f"/moves/{rule.target.name}/{move['source_id']}/back",
                          "label": reminder_moves.words(rule, "back")}] if rule.source is not None else []
                found.append({"words": escape(text), "forms": forms, "earlier": earlier, "key": "target_moved"})
            elif move["state"] == reminder_moves.RETURNED:
                forms = [{"action": f"/moves/{rule.target.name}/{move['source_id']}/move",
                          "label": "Move here again"}] if rule.source is not None else []
                found.append({"words": escape(reminder_moves.words(rule, "returned")), "forms": forms,
                              "earlier": earlier, "key": "returned"})
    return found


def _rule_or_404(store, target: str) -> reminder_moves.Rule:
    rule = reminder_moves.rule_for(store.registry, target, current_app.config.get("LOADED") or [])
    if rule is None:
        abort(404)
    return rule


def _backup():
    data_dir = current_app.config.get("DATA_DIR")
    if data_dir is not None:
        backups.before_move(data_dir, current_app.config.get("EXTRA_BACKUP_DIR"))


@moves_pages.get("/moves/<target>")
def review(target):
    """Review and move: every older record by its vehicle, name, date and permanent ID, one choice per row."""
    store = _store()
    rule = _rule_or_404(store, target)
    if not rule.target_on or rule.source is None:
        abort(404)
    rows = []
    for c in reminder_moves.candidates(store.conn, store.registry, rule):
        links = [display.Formatter(store).text(rule.source, rule.source.table.columns[s], c["row"].get(s))
                 for t, s in rule.copy.items() if rule.source.table.columns[s].type == "link"]
        rows.append(dict(c, link=", ".join(x for x in links if x), when=_date_words(store, c["date"]),
                         href=f"/t/{rule.source_name}/{c['id']}",
                         target_href=f"/t/{rule.target.name}/{c['target_id']}" if c["target_id"] else None))
    done = None
    if request.args.get("moved"):
        done = reminder_moves.words(rule, "moved", name=request.args.get("moved", "")[:120])
    return render_template("moves.html", rule=rule, rows=rows, done=done,
                           title=reminder_moves.words(rule, "title"),
                           intro=reminder_moves.words(rule, "intro", count=len(rows)),
                           warning=reminder_moves.words(rule, "warning"),
                           question=reminder_moves.words(rule, "question"),
                           no_date=reminder_moves.words(rule, "no_date"),
                           keep=reminder_moves.words(rule, "keep"), later=reminder_moves.words(rule, "later"),
                           back=reminder_moves.words(rule, "back"), source_module=rule.source.module.title,
                           target_title=display.table_title(rule.target),
                           choice=reminder_moves.choice(store.conn, rule))


@moves_pages.post("/moves/<target>/choice")
def choose(target):
    """Keep reminders where they are, Review and move, or Decide later: nothing moves by this alone."""
    store = _store()
    rule = _rule_or_404(store, target)
    value = request.form.get("choice", "")
    if value not in reminder_moves.CHOICES or not rule.target_on:
        abort(400)
    reminder_moves.choose(store.conn, rule, value)
    return redirect(f"/moves/{target}" if value == "review" else f"/t/{target}")


def _back_to(default: str) -> str:
    back = request.form.get("back", "")
    return back if back.startswith(("/t/", "/moves/")) and "//" not in back else default


@moves_pages.post("/moves/<target>/<int:source_id>/<act>")
def act(target, source_id, act):
    """Move one record, keep it, ask again later, or Transfer back."""
    store = _store()
    rule = _rule_or_404(store, target)
    if act not in ("move", "keep", "later", "back"):
        abort(404)
    try:
        if act == "move":
            result = reminder_moves.move(store, rule, source_id, backup=_backup)
            name = str((_row(store, rule.target.name, result["target_id"]) or {}).get("name") or "")
            return redirect(f"/t/{rule.target.name}/{result['target_id']}?moved=1"
                            if request.form.get("back") is None else
                            _back_to(f"/moves/{target}") + f"?moved={quote(name)}")
        if act == "back":
            reminder_moves.move_back(store, rule, source_id, backup=_backup)
            return redirect(f"/t/{rule.source_name}/{source_id}?returned=1")
        if act == "keep":
            reminder_moves.keep(store, rule, source_id)
        else:
            reminder_moves.later(store, rule, source_id)
    except records.RecordNotFound:
        abort(404)
    except PlainError as error:
        return render_template("moves_refused.html", message=str(error), back=_back_to(f"/t/{target}")), 409
    return redirect(_back_to(f"/moves/{target}"))
