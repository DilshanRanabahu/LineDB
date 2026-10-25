import pytest

from linedb import Database
from linedb.shell import run_shell, schema_text, split_statements


def run_session(monkeypatch, capsys, db, lines):
    """Feed lines to the shell as if typed, then return everything printed."""
    typed = iter(lines)

    def fake_input(prompt):
        try:
            return next(typed)
        except StopIteration:
            raise EOFError          # like pressing Ctrl+Z / Ctrl+D

    monkeypatch.setattr("builtins.input", fake_input)
    run_shell(db)
    return capsys.readouterr().out


@pytest.mark.parametrize("text, expected", [
    # one complete statement
    ("SELECT * FROM users;", (["SELECT * FROM users;"], "")),
    # not finished yet: everything is leftover
    ("SELECT * FROM", ([], "SELECT * FROM")),
    # several statements on one line
    ("A; B; C", (["A;", " B;"], " C")),
    # a ';' inside a string does not end the statement
    ("INSERT INTO t VALUES ('a;b');", (["INSERT INTO t VALUES ('a;b');"], "")),
    # an escaped quote ('') inside a string
    ("INSERT INTO t VALUES ('it''s; fine');",
     (["INSERT INTO t VALUES ('it''s; fine');"], "")),
    # an unfinished string keeps everything as leftover
    ("INSERT INTO t VALUES ('abc;", ([], "INSERT INTO t VALUES ('abc;")),
])
def test_split_statements(text, expected):
    assert split_statements(text) == expected


def test_schema_text(db):
    table = db.create_table("users", {"id": "INT", "name": "TEXT"})
    assert schema_text(table) == "CREATE TABLE users (id INT, name TEXT);"


def test_full_session(monkeypatch, capsys, db):
    out = run_session(monkeypatch, capsys, db, [
        "CREATE TABLE users (id INT, name TEXT, age INT);",
        "INSERT INTO users VALUES (1, 'Kamal', 22);",
        "INSERT INTO users VALUES (2, 'Nimali', 25); "
        "INSERT INTO users VALUES (3, 'Saman', 30);",
        "SELECT name FROM users",             # a statement over two lines
        "  WHERE age >= 25 ORDER BY age DESC LIMIT 1;",
        "UPDATE users SET age = 40;",
        "DELETE FROM users WHERE id != 1;",
        "SELECT * FROM users;",
        ".tables",
        ".schema users",
        "SELECT * FROM nothing;",             # errors are printed, not raised
        "SELEC oops;",
        "DROP TABLE users;",
        ".tables",
        "exit",
        "SELECT * FROM never_run;",           # after exit: must not run
    ])
    assert out.split("\n") == [
        "LineDB shell. Type .help for help, exit to quit.",
        "Table 'users' created",
        "1 row inserted",
        "1 row inserted",
        "1 row inserted",
        "name",
        "-----",
        "Saman",
        "(1 row)",
        "3 rows updated",
        "2 rows deleted",
        "id | name  | age",
        "---+-------+----",
        "1  | Kamal | 40",
        "(1 row)",
        "users",
        "CREATE TABLE users (id INT, name TEXT, age INT);",
        "Error: No such table: nothing",
        "Error: Unsupported statement: 'SELEC'",
        "Table 'users' dropped",
        "",
    ]
    assert db.tables == {}


def test_data_survives_shell_restart(monkeypatch, capsys, db):
    run_session(monkeypatch, capsys, db, [
        "CREATE TABLE t (id INT);",
        "INSERT INTO t VALUES (7);",
    ])
    out = run_session(monkeypatch, capsys, Database(db.folder), [
        "SELECT * FROM t;",
    ])
    assert "7" in out.split("\n")