"""One-page printable sheets declared by modules, such as the emergency sheet."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import records
from dashboard.core.schema import join_table_name, table_name, target_table
from dashboard.web import display

sheet_pages = Blueprint("sheets", __name__)
ROW_LIMIT = 200


def available_sheets(registry: dict) -> list[dict]:
    """Sheets of the modules that are switched on, for the home page."""
    seen, sheets = set(), []
    for info in registry.values():
        module = info.module
        if module.name in seen:
            continue
        seen.add(module.name)
        sheets += [{"module": module.name, "name": s["name"], "title": s["title"]} for s in module.sheets]
    return sheets


def _where_value(value):
    return int(value) if isinstance(value, bool) else value


@sheet_pages.route("/sheet/<module>/<name>", methods=["GET", "POST"])
def show_sheet(module, name):
    registry = current_app.config["REGISTRY_FOR_REQUEST"]()
    modules = {info.module.name: info.module for info in registry.values()}
    if module not in modules:
        abort(404)
    sheet = next((s for s in modules[module].sheets if s["name"] == name), None)
    if sheet is None:
        abort(404)
    conn = current_app.config["CONNECT"]()
    formatter = display.Formatter(records.Records(conn, registry))
    sections, private = [], False
    for section in sheet["sections"]:
        info = registry[table_name(module, section["table"])]
        columns = []  # (label, how to read the value, column used for formatting, table info for formatting)
        for spec in section["columns"]:
            if "." in spec:
                link, _, field_name = spec.partition(".")
                # The linked record may be in this module or one it requires, like People (decision 0072).
                target = registry.get(target_table(module, info.table.columns[link]))
                if target is None:
                    continue
                column = target.table.columns[field_name]
                columns.append((display.column_label(target, column), link, field_name, column, target))
            else:
                column = info.table.columns[spec]
                columns.append((display.column_label(info, column), spec, None, column, info))
        private = private or any(c[3].sensitive for c in columns)
        clause = ""
        for c in section["where"]:
            link, _, field_name = c.partition(".")
            if field_name:  # a column of the linked record, such as an item's category for its batches
                target = registry[table_name(module, info.table.columns[link].to)]
                clause += f" AND {link} IN (SELECT id FROM {target.name} WHERE {field_name} = ?)"
            else:
                clause += f" AND {c} = ?"
        if info.table.total:  # a used-up batch is history, not something to find in an emergency
            clause += f" AND {info.table.total['amount']} > 0"
        rows = conn.execute(
            f"SELECT * FROM {info.name} WHERE deleted_at IS NULL{clause} "
            f"ORDER BY {section['order_by']} IS NULL, {section['order_by']}, id LIMIT {ROW_LIMIT}",  # blanks last
            [_where_value(v) for v in section["where"].values()]).fetchall()
        linked: dict[tuple[str, int], dict] = {}

        def value(row, spec):
            label, name, field_name, column, owner = spec
            if field_name is None and column.type == "links":  # several records, kept in a join table
                join = join_table_name(module, info.table.name, name)
                ids = [r[0] for r in conn.execute(f"SELECT to_id FROM {join} WHERE from_id = ? ORDER BY to_id", (row["id"],))]
                return formatter.text(owner, column, ids)
            if field_name is None:
                return formatter.text(owner, column, row.get(name))
            record_id = row.get(name)
            if record_id is None:
                return ""
            key = (owner.name, record_id)
            if key not in linked:
                linked[key] = conn.execute(f"SELECT * FROM {owner.name} WHERE id = ?", (record_id,)).fetchone()
            target_row = linked[key]
            if target_row is None or target_row["deleted_at"]:
                return ""
            return formatter.text(owner, column, dict(target_row).get(field_name))

        sections.append({"title": section["title"], "headings": [c[0] for c in columns],
                         "rows": [[value(dict(r), c) for c in columns] for r in rows]})
    if private and request.method != "POST":
        # A sheet with private details opens only by choice (decision 0071): the button POSTs, so no
        # address, bookmark or shared link can open it, and ?show=1 does nothing.
        return render_template("private_sheet.html", sheet=sheet, module=module, name=name)
    return render_template("sheet.html", sheet=sheet, sections=sections, private=private,
                           printed=date.today().strftime("%d %B %Y"))
