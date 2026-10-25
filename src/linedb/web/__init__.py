"""A small Flask web UI for LineDB.

Run it with:  python -m linedb.web [folder]
"""
import sys
import threading

from flask import Flask, jsonify, render_template, request

from ..executor import run
from ..shell import split_statements
from ..storage import TYPES, Database


def _statements(text):
    """Cut the editor text into statements. The last ';' is optional."""
    statements, rest = split_statements(text)
    if rest.strip():
        statements.append(rest)
    return [s for s in statements if s.strip() not in ("", ";")]


def _result_json(sql, result):
    return {
        "sql": sql.strip(),
        "message": result.message,
        "columns": result.columns,
        "rows": result.rows,
    }


def create_app(folder="db_data"):
    app = Flask(__name__)
    db = Database(folder)
    # LineDB has no file locking of its own, and Flask serves requests on
    # several threads, so only one request at a time may touch the files.
    lock = threading.Lock()

    @app.get("/")
    def index():
        return render_template("index.html", folder=folder)

    @app.get("/api/tables")
    def tables():
        with lock:
            return jsonify(
                types=list(TYPES),
                tables=[
                    {
                        "name": name,
                        "columns": [
                            {"name": column, "type": type_name}
                            for column, type_name in table.schema.items()
                        ],
                    }
                    for name, table in sorted(db.tables.items())
                ],
            )

    @app.post("/api/query")
    def query():
        """Run one or more statements. Stops at the first error.

        Statements before the error have already been applied (there are
        no transactions yet), so their results are sent back as well.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("sql"), str):
            return jsonify(results=[],
                           error='Send JSON like {"sql": "SELECT ..."}'), 400
        statements = _statements(data["sql"])
        if not statements:
            return jsonify(results=[], error="Empty statement"), 400

        results = []
        with lock:
            for sql in statements:
                try:
                    results.append(_result_json(sql, run(db, sql)))
                except ValueError as e:         # includes SQLSyntaxError
                    return jsonify(results=results, error=str(e)), 400
                except Exception as e:          # a bug in LineDB itself
                    app.logger.exception("internal error running %r", sql)
                    return jsonify(
                        results=results,
                        error=f"Internal error: {type(e).__name__}: {e}",
                    ), 500
        return jsonify(results=results, error=None)

    return app


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    folder = argv[0] if argv else "db_data"
    print(f"LineDB web UI on http://127.0.0.1:5000  (database folder: {folder})")
    # 127.0.0.1 only: there is no login, so do not expose this to a network
    create_app(folder).run(host="127.0.0.1", port=5000)
