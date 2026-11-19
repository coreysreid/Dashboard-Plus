"""Settings, Export my records: a page and a button that downloads a zip of spreadsheet files."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, Response, current_app, render_template, request

from dashboard import __version__
from dashboard.core import export

export_pages = Blueprint("export_pages", __name__)


def _tables() -> list[dict]:
    """The lists that would be exported: every table of a module that is switched on."""
    from dashboard.web.display import table_title
    registry = current_app.config["REGISTRY_FOR_REQUEST"]()
    return [{"title": table_title(info), "module": info.module.title} for info in registry.values()]


@export_pages.get("/settings/export")
def export_page():
    return render_template("export.html", tables=_tables())


@export_pages.post("/settings/export")
def export_download():
    data = export.build(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"](), __version__,
                        include_deleted=bool(request.form.get("include_deleted")))
    name = f"dashboard-plus-export-{date.today().isoformat()}.zip"
    return Response(data, mimetype="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})
