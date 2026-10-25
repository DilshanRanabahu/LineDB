import json
import logging
import operator
import os

log = logging.getLogger(__name__)

# Supported column types and the Python type each one maps to.
TYPES = {"INT": int, "TEXT": str}

# Comparison operators allowed in a WHERE condition.
OPERATORS = {
    "=": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _type_ok(type_name, value):
    """True if value matches the column type. bool is rejected for INT."""
    if type_name == "INT":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, TYPES[type_name])


class Table:
    """A small table stored as a JSON Lines file (one row per line)."""

    def __init__(self, name, schema, folder="."):
        self.name = name
        self.schema = dict(schema)          # {"id": "INT", "name": "TEXT"}
        self.columns = list(self.schema)    # column names in schema order
        self.path = os.path.join(folder, f"{name}.jsonl")

    # ---------- helpers ----------

    def _check_column(self, column):
        if column not in self.schema:
            raise ValueError(f"Unknown column: {column}")

    def _check_values(self, values):
        """Check that every value matches its column type."""
        for col, val in values.items():
            self._check_column(col)
            type_name = self.schema[col]
            if not _type_ok(type_name, val):
                raise ValueError(
                    f"Column '{col}' expects {type_name}, got {val!r} "
                    f"({type(val).__name__})"
                )

    def _ensure_trailing_newline(self):
        """If the last write was cut off (no newline at the end), close that
        broken line so the next row starts on a fresh line."""
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return
        with open(self.path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            last_byte = f.read(1)
        if last_byte != b"\n":
            with open(self.path, "ab") as g:
                g.write(b"\n")

    def _rewrite(self, transform):
        """Rewrite the whole file through a temp file.

        transform(row) must return the new row, the same row (unchanged),
        or None (delete the row). Returns how many rows were changed.
        Corrupt lines are copied over unchanged, so they are never lost.
        """
        if not os.path.exists(self.path):
            return 0
        tmp_path = self.path + ".tmp"
        changed = 0
        with open(self.path, encoding="utf-8") as src, \
                open(tmp_path, "w", encoding="utf-8") as out:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("corrupt line kept as-is in %s", self.path)
                    out.write(line + "\n")
                    continue
                new_row = transform(row)
                if new_row is not row:
                    changed += 1
                if new_row is not None:
                    out.write(json.dumps(new_row, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp_path, self.path)
        return changed

    # ---------- operations ----------

    def insert(self, row):
        if set(row) != set(self.columns):
            raise ValueError(f"Expected columns {self.columns}, got {list(row)}")
        self._check_values(row)
        # keep the schema column order, whatever order the caller used
        row = {c: row[c] for c in self.columns}

        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        self._ensure_trailing_newline()

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def select_all(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    log.warning("corrupt line skipped in %s", self.path)
                    continue

    def _matcher(self, where):
        """Turn a WHERE condition into a function row -> True/False.

        where is None (every row matches) or a (column, op, value) tuple,
        for example ("age", ">", 20).
        """
        if where is None:
            return lambda row: True
        column, op, value = where
        if op not in OPERATORS:
            raise ValueError(f"Unknown operator: {op}")
        self._check_values({column: value})
        compare = OPERATORS[op]
        type_name = self.schema[column]

        def matches(row):
            cell = row.get(column)
            # a cell with the wrong type (file edited by hand) never matches
            return _type_ok(type_name, cell) and compare(cell, value)

        return matches

    def select(self, where=None):
        matches = self._matcher(where)
        return [r for r in self.select_all() if matches(r)]

    def update(self, changes, where=None):
        matches = self._matcher(where)
        self._check_values(changes)

        def transform(row):
            if matches(row):
                return {**row, **changes}
            return row

        return self._rewrite(transform)

    def delete(self, where=None):
        matches = self._matcher(where)

        def transform(row):
            return None if matches(row) else row

        return self._rewrite(transform)


class Database:
    """A folder that holds a catalog (schemas) and one data file per table."""

    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.catalog_path = os.path.join(folder, "catalog.json")
        self.tables = {}
        self._load_catalog()

    def _load_catalog(self):
        if not os.path.exists(self.catalog_path):
            return
        with open(self.catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)
        for name, schema in catalog.items():
            self.tables[name] = Table(name, schema, self.folder)

    def _save_catalog(self):
        catalog = {name: t.schema for name, t in self.tables.items()}
        tmp_path = self.catalog_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # atomic swap, same trick as in Table._rewrite
        os.replace(tmp_path, self.catalog_path)

    def create_table(self, name, schema):
        if not name or not name.isidentifier():
            raise ValueError(f"Invalid table name: {name!r}")
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")
        if not schema:
            raise ValueError("A table needs at least one column")
        for col, type_name in schema.items():
            if type_name not in TYPES:
                raise ValueError(
                    f"Unknown type '{type_name}' for column '{col}'. "
                    f"Supported: {sorted(TYPES)}"
                )
        self.tables[name] = Table(name, schema, self.folder)
        self._save_catalog()
        return self.tables[name]

    def drop_table(self, name):
        table = self.table(name)        # raises if there is no such table
        # Delete the data before the catalog entry. If we crash in between,
        # the table is still listed but empty; the other way round, an
        # orphan file would come back on the next CREATE TABLE.
        for path in (table.path, table.path + ".tmp"):
            if os.path.exists(path):
                os.remove(path)
        del self.tables[name]
        self._save_catalog()

    def table(self, name):
        if name not in self.tables:
            raise ValueError(f"No such table: {name}")
        return self.tables[name]