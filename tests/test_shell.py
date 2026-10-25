import pytest

from linedb.shell import schema_text, split_statements


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
