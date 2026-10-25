from .parser import parse


def _rows(count):
    """'1 row' or '3 rows'."""
    return f"{count} row{'' if count == 1 else 's'}"


def format_table(names, rows):
    """Draw rows as a simple text table."""
    cells = [[str(value) for value in row] for row in rows]
    widths = [
        max([len(name)] + [len(row[i]) for row in cells])
        for i, name in enumerate(names)
    ]
    header = " | ".join(name.ljust(w) for name, w in zip(names, widths)).rstrip()
    line = "-+-".join("-" * w for w in widths)
    body = [
        " | ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip()
        for row in cells
    ]
    count = f"({_rows(len(rows))})"
    return "\n".join([header, line] + body + [count])


def _where(statement):
    """The statement's WHERE as a (column, op, value) tuple, or None."""
    where = statement["where"]
    if where is None:
        return None
    return (where["column"], where["op"], where["value"])


def _check_columns(table, names):
    for name in names:
        if name not in table.schema:
            raise ValueError(f"Unknown column: {name}")


# ---------- one function per statement type ----------

def _create_table(db, statement):
    db.create_table(statement["table"], statement["columns"])
    return f"Table '{statement['table']}' created"


def _drop_table(db, statement):
    db.drop_table(statement["table"])
    return f"Table '{statement['table']}' dropped"


def _insert(db, statement):
    table = db.table(statement["table"])
    values = statement["values"]
    if len(values) != len(table.columns):
        raise ValueError(
            f"Table '{table.name}' has {len(table.columns)} columns "
            f"but {len(values)} values were given"
        )
    # values arrive in column order, so pair them up with the names
    table.insert(dict(zip(table.columns, values)))
    return "1 row inserted"


def _select(db, statement):
    table = db.table(statement["table"])

    # which columns to show, and which ones to sort by
    names = statement["columns"] or table.columns
    order_by = statement["order_by"]
    _check_columns(table, names)
    _check_columns(table, [item["column"] for item in order_by])

    # which rows to show
    rows = table.select(_where(statement))

    # Sort by the last key first. Python's sort is stable, so after the
    # final pass the first ORDER BY column decides, and later ones break ties.
    for item in reversed(order_by):
        column = item["column"]
        rows.sort(key=lambda row: row[column], reverse=item["descending"])

    if statement["limit"] is not None:
        rows = rows[:statement["limit"]]

    return format_table(names, [[row[n] for n in names] for row in rows])


def _update(db, statement):
    table = db.table(statement["table"])
    count = table.update(statement["changes"], _where(statement))
    return f"{_rows(count)} updated"


def _delete(db, statement):
    table = db.table(statement["table"])
    count = table.delete(_where(statement))
    return f"{_rows(count)} deleted"


HANDLERS = {
    "create_table": _create_table,
    "drop_table": _drop_table,
    "insert": _insert,
    "select": _select,
    "update": _update,
    "delete": _delete,
}


def execute(db, sql):
    """Parse one SQL statement and run it on the database.

    Returns text describing the result.
    """
    statement = parse(sql)
    handler = HANDLERS.get(statement["type"])
    if handler is None:
        raise ValueError(f"Cannot execute statement type: {statement['type']}")
    return handler(db, statement)
