import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("flask")

from linedb.web import create_app  # noqa: E402

APP_JS = Path(__file__).parent.parent / "src" / "linedb" / "web" / "static" / "app.js"


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path))
    app.testing = True
    return app.test_client()


def query(client, sql):
    response = client.post("/api/query", json={"sql": sql})
    return response.status_code, response.get_json()


# ---------- pages ----------

def test_index_page(client, tmp_path):
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "<title>LineDB</title>" in page
    assert "/static/app.js" in page and "/static/style.css" in page
    assert str(tmp_path) in page        # the folder name is shown


@pytest.mark.parametrize("path", ["/static/app.js", "/static/style.css"])
def test_static_files(client, path):
    response = client.get(path)
    assert response.status_code == 200
    response.close()


def test_folder_name_is_escaped(tmp_path):
    # '<' is not allowed in Windows folder names, but '&' and "'" are
    folder = tmp_path / "Tom & Jerry's"
    client = create_app(str(folder)).test_client()
    page = client.get("/").get_data(as_text=True)
    assert "Tom & Jerry's" not in page
    assert "Tom &amp; Jerry&#39;s" in page


# ---------- /api/tables ----------

def test_tables(client):
    assert client.get("/api/tables").get_json() == {
        "types": ["INT", "TEXT"], "tables": [],
    }
    query(client, "CREATE TABLE users (id INT, name TEXT)")
    query(client, "CREATE TABLE a_first (x INT)")
    assert client.get("/api/tables").get_json()["tables"] == [
        {"name": "a_first", "columns": [{"name": "x", "type": "INT"}]},
        {"name": "users", "columns": [
            {"name": "id", "type": "INT"}, {"name": "name", "type": "TEXT"},
        ]},
    ]


# ---------- /api/query ----------

def test_select_returns_columns_and_rows(client):
    query(client, "CREATE TABLE users (id INT, name TEXT)")
    query(client, "INSERT INTO users VALUES (1, 'Kamal')")
    status, data = query(client, "SELECT * FROM users;")
    assert status == 200
    assert data == {
        "error": None,
        "results": [{
            "sql": "SELECT * FROM users;",
            "message": "1 row",
            "columns": ["id", "name"],
            "rows": [[1, "Kamal"]],
        }],
    }


def test_other_statements_return_a_message(client):
    status, data = query(client, "CREATE TABLE t (id INT)")
    assert status == 200
    assert data["results"] == [{
        "sql": "CREATE TABLE t (id INT)", "message": "Table 't' created",
        "columns": None, "rows": None,
    }]


def test_several_statements(client):
    status, data = query(client, """
        CREATE TABLE t (id INT, s TEXT);
        INSERT INTO t VALUES (1, 'a;b');
        INSERT INTO t VALUES (2, 'c');
        SELECT s FROM t ORDER BY id DESC
    """)
    assert status == 200
    assert [r["message"] for r in data["results"]] == [
        "Table 't' created", "1 row inserted", "1 row inserted", "2 rows",
    ]
    assert data["results"][-1]["rows"] == [["c"], ["a;b"]]


def test_stops_at_first_error(client):
    status, data = query(client, """
        CREATE TABLE t (id INT);
        INSERT INTO t VALUES ('bad');
        INSERT INTO t VALUES (2);
    """)
    assert status == 400
    assert [r["message"] for r in data["results"]] == ["Table 't' created"]
    assert "expects INT" in data["error"]
    # the statement after the error did not run
    assert query(client, "SELECT * FROM t")[1]["results"][0]["rows"] == []


@pytest.mark.parametrize("sql, message", [
    ("SELEC * FROM t", "Unsupported statement"),
    ("SELECT * FROM nothing", "No such table"),
    ("SELECT * FROM t WHERE", "Expected a column name"),
    ("INSERT INTO t VALUES ('abc", "Unterminated string"),
])
def test_errors(client, sql, message):
    query(client, "CREATE TABLE t (id INT)")
    status, data = query(client, sql)
    assert status == 400
    assert message in data["error"]


@pytest.mark.parametrize("body", [
    None,
    "not json",
    json.dumps([1, 2]),
    json.dumps({"query": "SELECT 1"}),
    json.dumps({"sql": 42}),
])
def test_bad_request_body(client, body):
    response = client.post("/api/query", data=body,
                           content_type="application/json")
    assert response.status_code == 400
    assert "Send JSON" in response.get_json()["error"]


@pytest.mark.parametrize("sql", ["", "   ", ";", " ; ; "])
def test_empty_sql(client, sql):
    status, data = query(client, sql)
    assert status == 400
    assert data["error"] == "Empty statement"


def test_internal_error_is_json(client, monkeypatch):
    def broken(db, sql):
        raise KeyError("oops")
    monkeypatch.setattr("linedb.web.run", broken)
    status, data = query(client, "SELECT * FROM t")
    assert status == 500
    assert data["error"].startswith("Internal error: KeyError")


def test_data_is_shared_with_the_shell(tmp_path):
    from linedb import Database, execute
    client = create_app(str(tmp_path)).test_client()
    query(client, "CREATE TABLE t (id INT)")
    query(client, "INSERT INTO t VALUES (5)")
    assert "5" in execute(Database(str(tmp_path)), "SELECT * FROM t")


# ---------- the SQL that app.js builds ----------

node = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")

JS_CASES = r"""
const sql = require(process.argv[1]);
const cols = [{name: "id", type: "INT"}, {name: "name", type: "TEXT"}];
const out = {
  literals: [
    sql.sqlLiteral(42, "INT"), sql.sqlLiteral(" -7 ", "INT"),
    sql.sqlLiteral("O'Brien", "TEXT"), sql.sqlLiteral("", "TEXT"),
    sql.sqlLiteral("a;b''c", "TEXT"),
  ],
  statements: [
    sql.createTableSql("people", cols),
    sql.insertSql("people", cols, ["1", "Kamal"]),
    sql.insertSql("people", cols, ["2", "O'Brien; DROP TABLE people"]),
    sql.updateSql("people", cols, ["1", "Kamal P"], cols[0], 1),
    sql.selectAllSql("people"),
    sql.deleteSql("people", cols[1], "O'Brien; DROP TABLE people"),
    sql.selectAllSql("people"),
    sql.dropTableSql("people"),
  ],
  errors: [],
};
for (const bad of [
  () => sql.sqlLiteral("12a", "INT"),
  () => sql.sqlLiteral("", "INT"),
  () => sql.sqlLiteral("1.5", "INT"),
  () => sql.createTableSql("1bad", cols),
  () => sql.createTableSql("ok", []),
  () => sql.createTableSql("ok", [{name: "has space", type: "INT"}]),
  () => sql.insertSql("people", cols, ["x", "Kamal"]),
]) {
  try { bad(); out.errors.push(null); } catch (e) { out.errors.push(e.message); }
}
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    result = subprocess.run(
        ["node", "-e", JS_CASES, str(APP_JS)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


@node
def test_js_literals(js):
    assert js["literals"] == ["42", "-7", "'O''Brien'", "''", "'a;b''''c'"]


@node
def test_js_rejects_bad_input(js):
    assert all(js["errors"]), js["errors"]
    assert "not a whole number" in js["errors"][0]
    assert "Table name" in js["errors"][3]


@node
def test_js_statements_run_on_the_server(js, client):
    # every statement the UI would build must be valid LineDB SQL
    results = []
    for sql in js["statements"]:
        status, data = query(client, sql)
        assert status == 200, (sql, data)
        results.append(data["results"][0])

    assert [r["message"] for r in results] == [
        "Table 'people' created", "1 row inserted", "1 row inserted",
        "1 row updated", "2 rows", "1 row deleted", "1 row",
        "Table 'people' dropped",
    ]
    # a quote and ';' inside a value stay part of the value
    assert results[4]["rows"] == [
        [1, "Kamal P"], [2, "O'Brien; DROP TABLE people"],
    ]
    assert results[6]["rows"] == [[1, "Kamal P"]]
