"""Settings, Backups: the list of backups, a preview of one, putting it back, and Undo restore."""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import records, restore
from dashboard.web.display import table_title

restore_pages = Blueprint("restore", __name__)


def _folders() -> dict:
    return restore.folders(current_app.config["DATA_DIR"], current_app.config["EXTRA_BACKUP_DIR"],
                           current_app.config["CONNECT"]())


def _tracks() -> dict:
    return restore.known_tracks(current_app.config["LOADED"])


def when(moment: datetime | str | None) -> str:
    """A time the way the backup pages show it: 18 Nov 2026 at 14:35."""
    if isinstance(moment, str):
        try:
            moment = datetime.fromisoformat(moment)
        except ValueError:
            return moment
    return moment.strftime("%d %b %Y at %H:%M").lstrip("0") if moment else ""


def size(count: int) -> str:
    """A file size in words a household knows: 84 KB, 1.2 MB."""
    if count < 1024 * 1024:
        return f"{max(1, round(count / 1024))} KB"
    return f"{count / (1024 * 1024):.1f} MB"


def _undo_offer() -> dict | None:
    found = restore.journal(current_app.config["DATA_DIR"])
    if not found:
        return None
    source = found.get("from", {}) if isinstance(found.get("from"), dict) else {}
    return {"at": when(found.get("restored_at")), "made": when(source.get("made")),
            "where": restore.PLACES.get(source.get("place"), "")}


def _copy_or_404(place: str, name: str):
    copy = restore.get(_folders(), place, name)
    if copy is None:
        return None, (render_template("error.html", message="That backup could not be found. It may have been "
                                                            "removed. Go back to the list of backups."), 404)
    return copy, None


@restore_pages.get("/settings/backups")
def backup_list():
    copies = [restore.check(c, _tracks()) for c in restore.find(_folders())]
    return render_template("restore_list.html", copies=copies, when=when, size=size, undo=_undo_offer(),
                           kept=request.args.get("kept") == "1")


def _preview(copy, problem: str | None = None, status: int = 200):
    restore.check(copy, _tracks(), full=True)
    rows = []
    if copy.usable:
        registry = records.build_registry(current_app.config["LOADED"])
        then = restore.copy_counts(copy, list(registry))
        now = restore.counts(current_app.config["CONNECT"](), list(registry))
        for name, info in registry.items():
            if now.get(name) or then.get(name):
                rows.append({"title": table_title(info), "area": info.module.title, "now": now.get(name) or 0,
                             "then": then.get(name), "differs": (then.get(name) or 0) != (now.get(name) or 0)})
        rows.sort(key=lambda r: (r["area"].lower(), r["title"].lower()))
    return render_template("restore_preview.html", copy=copy, rows=rows, when=when, size=size,
                           problem=problem, undo=_undo_offer()), status


@restore_pages.get("/settings/backups/<place>/<name>")
def preview(place: str, name: str):
    copy, missing = _copy_or_404(place, name)
    return missing or _preview(copy)


@restore_pages.post("/settings/backups/<place>/<name>/restore")
def put_back(place: str, name: str):
    copy, missing = _copy_or_404(place, name)
    if missing:
        return missing
    current_app.config["RELEASE"]()  # this page's own connection must not hold the data file open
    try:
        restore.restore(current_app.config["DATA_DIR"], copy, current_app.config["LOADED"],
                        seen=request.form.get("seen", ""))
    except restore.RestoreError as error:
        return _preview(copy, problem=str(error), status=409)
    return redirect(url_for("restore.restored"))


@restore_pages.get("/settings/backups/restored")
def restored():
    offer = _undo_offer()
    if offer is None:
        return redirect(url_for("restore.backup_list"))
    return render_template("restore_done.html", undone=False, undo=offer, problem=None)


@restore_pages.post("/settings/backups/undo")
def undo():
    current_app.config["RELEASE"]()
    try:
        restore.undo(current_app.config["DATA_DIR"], current_app.config["LOADED"])
    except restore.RestoreError as error:
        return render_template("restore_done.html", undone=False, undo=_undo_offer(), problem=str(error)), 409
    return render_template("restore_done.html", undone=True, undo=None, problem=None)


@restore_pages.post("/settings/backups/keep")
def keep():
    restore.dismiss(current_app.config["DATA_DIR"])
    return redirect(url_for("restore.backup_list", kept="1"))
