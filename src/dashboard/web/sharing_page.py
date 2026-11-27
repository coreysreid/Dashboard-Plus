"""Settings, What your other computers get: each list and its details shared or kept here, a confirmation before sharing anything private, and Undo (decision 0140)."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request

from dashboard.core import dates
from dashboard.core import sync_sharing as sharing
from dashboard.web.display import column_label, table_title

sharing_pages = Blueprint("sharing_pages", __name__)
PREFIX = "c:"
OUT_OF_DATE = "These choices changed while the page was open, so nothing was changed. Check them and choose again."


def _conn():
    return current_app.config["CONNECT"]()


def _registry() -> dict:
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _words(registry, key: str, choice: str) -> str:
    table, _, column = key.partition(".")
    info = registry[table]
    if not column:
        return sharing.list_words(info, choice)
    found = info.table.columns[column]
    return sharing.detail_words(found, choice, sharing.kinds_words(info, found))


def _name(registry, key: str) -> str:
    table, _, column = key.partition(".")
    info = registry.get(table)
    if info is None:
        return "A list that is switched off"
    if not column:
        return table_title(info)
    found = info.table.columns.get(column)
    return f"{table_title(info)}, {column_label(info, found) if found else column.replace('_', ' ')}"


def _groups(conn, registry) -> list[dict]:
    """Module by module, each list with its choice and each detail with its own, in the household's words."""
    now = sharing.current(conn, registry)
    groups: dict[str, dict] = {}
    for name, info in registry.items():
        group = groups.setdefault(info.module.name, {"title": info.module.title, "lists": []})
        usual = sharing.list_default(info)
        details = []
        for column in info.table.columns.values():
            key = f"{name}.{column.name}"
            reason = sharing.fixed_reason(column)
            options = sharing.detail_options(column)
            details.append({
                "key": key, "label": column_label(info, column), "private": column.sensitive, "fixed": reason,
                "choice": now.get(key, "local"),
                "usual": _words(registry, key, sharing.detail_default(column)),
                "changed": key in now and now[key] != sharing.detail_default(column),
                "options": [{"value": o, "words": _words(registry, key, o), "checked": now.get(key) == o}
                            for o in options]})
        group["lists"].append({
            "key": name, "title": table_title(info), "private": info.table.private or any(c.sensitive for c in
                                                                                         info.table.columns.values()),
            "choice": now[name], "usual": _words(registry, name, usual), "changed": now[name] != usual,
            "options": [{"value": o, "words": _words(registry, name, o), "checked": now[name] == o}
                        for o in sharing.list_options(info)],
            "kept_back": [column_label(info, c) for c in sharing.private_columns(info)],
            "details": details})
    return list(groups.values())


def _history(conn, registry) -> list[dict]:
    style = dates.household_style(conn)
    found = []
    for entry in sharing.history(conn):
        lines = []
        for key, after in sorted(entry["after"].items()):
            before = entry["before"].get(key)
            if key.partition(".")[0] not in registry:
                lines.append("A list that is switched off now")
                continue
            lines.append(f"{_name(registry, key)}: {_words(registry, key, before)} → {_words(registry, key, after)}"
                         if before else f"{_name(registry, key)}: {_words(registry, key, after)}")
        found.append({"id": entry["id"], "on": dates.show(entry["at"][:10], style), "lines": lines,
                      "undo": entry["action"] == "sharing_undo", "loosened": entry["loosened"],
                      "can_undo": sharing.undoable(conn, registry, entry)})
    return found


def _page(problem: str | None = None, status: int = 200, saved: list[int] = ()):
    conn, registry = _conn(), _registry()
    history = _history(conn, registry)
    just_saved = [h for h in history if h["id"] in saved]
    return render_template("sharing.html", groups=_groups(conn, registry), history=history, problem=problem,
                           just_saved=just_saved, undone=request.args.get("undone") == "1"), status


@sharing_pages.get("/settings/sharing")
def sharing_page():
    saved = [int(v) for v in request.args.get("saved", "").split(",") if v.isdigit()]
    return _page(saved=saved)


def _wanted(form, registry, now: dict) -> dict:
    """The choices on the form that differ from now. A key for a fixed detail is kept, so it is refused."""
    wanted = {}
    for field, value in form.items():
        if not field.startswith(PREFIX):
            continue
        key = field[len(PREFIX):]
        table, _, column = key.partition(".")
        info = registry.get(table)
        if info is None or (column and column not in info.table.columns):
            continue
        if now.get(key) != value:
            wanted[key] = value
    return wanted


def _starts_words(found: list[dict]) -> list[dict]:
    """What will start going to the other computers, list by list, in plain words."""
    lines = []
    for item in found:
        info = item["info"]
        parts = [column_label(info, c) + (" (private)" if c.sensitive else "") for c in item["columns"]]
        lines.append({"title": table_title(info), "list_starts": item["list_starts"], "details": parts,
                      "private": item["private"]})
    return lines


@sharing_pages.post("/settings/sharing")
def sharing_save():
    conn, registry = _conn(), _registry()
    now = sharing.current(conn, registry)
    wanted = _wanted(request.form, registry, now)
    try:
        sharing.check(registry, wanted)
    except sharing.SharingError as error:
        return _page(str(error), 400)
    tighter = {k: v for k, v in wanted.items() if not sharing.loosens(k, now[k], v)}
    looser = {k: v for k, v in wanted.items() if sharing.loosens(k, now[k], v)}
    saved = []
    if tighter:  # keeping something on this computer happens at once
        done = sharing.apply(conn, registry, tighter)
        if done:
            saved.append(done)
    if looser:
        found = sharing.starts(conn, registry, looser)
        if sharing.needs_confirmation(found):
            now = sharing.current(conn, registry)
            return render_template("sharing_confirm.html", starts=_starts_words(found),
                                   items=[{"key": k, "want": v, "was": now[k], "name": _name(registry, k),
                                           "words": _words(registry, k, v)} for k, v in sorted(looser.items())],
                                   kept_now=bool(saved))
        done = sharing.apply(conn, registry, looser)
        if done:
            saved.append(done)
    return redirect("/settings/sharing" + (f"?saved={','.join(map(str, saved))}" if saved else ""), 303)


@sharing_pages.post("/settings/sharing/confirm")
def sharing_confirm():
    conn, registry = _conn(), _registry()
    now = sharing.current(conn, registry)
    wanted, was = {}, {}
    for field, value in request.form.items():
        if field.startswith("want:"):
            wanted[field[5:]] = value
        elif field.startswith("was:"):
            was[field[4:]] = value
    if request.form.get("confirm") != "yes" or not wanted:
        return redirect("/settings/sharing", 303)
    if set(wanted) != set(was) or any(now.get(k) != v for k, v in was.items()):
        return _page(OUT_OF_DATE, 409)
    try:
        done = sharing.apply(conn, registry, wanted)
    except sharing.SharingError as error:
        return _page(str(error), 400)
    return redirect("/settings/sharing" + (f"?saved={done}" if done else ""), 303)


@sharing_pages.post("/settings/sharing/undo")
def sharing_undo():
    conn, registry = _conn(), _registry()
    entry = request.form.get("entry", "")
    if not entry.isdigit():
        return _page("Nothing was undone: that choice was not found.", 400)
    try:
        sharing.undo(conn, registry, int(entry))
    except sharing.SharingError as error:
        return _page(str(error), 409)
    return redirect("/settings/sharing?undone=1", 303)
