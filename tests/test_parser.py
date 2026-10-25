import pytest

from linedb import SQLSyntaxError, parse


def test_create_table():
    assert parse("CREATE TABLE users (id INT, name TEXT, age INT);") == {
        "type": "create_table", "table": "users",
        "columns": {"id": "INT", "name": "TEXT", "age": "INT"},
    }
    assert parse("create table notes (title TEXT)")["columns"] == {
        "title": "TEXT"
    }


def test_insert():
    assert parse("INSERT INTO users VALUES (1, 'Kamal', 22);") == {
        "type": "insert", "table": "users", "values": [1, "Kamal", 22],
    }
    assert parse("insert into users values (2, 'O''Brien', -5)")["values"] == [
        2, "O'Brien", -5
    ]


def test_select():
    assert parse("SELECT * FROM users;") == {
        "type": "select", "table": "users", "columns": None, "where": None,
    }
    assert parse("select name, age from users where id = 2") == {
        "type": "select", "table": "users", "columns": ["name", "age"],
        "where": {"column": "id", "value": 2},
    }


def test_update():
    assert parse("UPDATE users SET age = 23 WHERE id = 1;") == {
        "type": "update", "table": "users", "changes": {"age": 23},
        "where": {"column": "id", "value": 1},
    }
    statement = parse("update users set age = 30, name = 'Sam' where id = 2")
    assert statement["changes"] == {"age": 30, "name": "Sam"}


def test_delete():
    assert parse("DELETE FROM users WHERE id = 2") == {
        "type": "delete", "table": "users",
        "where": {"column": "id", "value": 2},
    }


@pytest.mark.parametrize("sql", [
    # general
    "",
    "DROP TABLE users",
    # CREATE TABLE
    "CREATE TABLE (id INT)",
    "CREATE TABLE t ()",
    "CREATE TABLE t (id FLOAT)",
    "CREATE TABLE t (id INT name TEXT)",
    "CREATE TABLE t (id INT, id TEXT)",
    "CREATE TABLE t (id INT",
    "CREATE TABLE t (id INT) extra",
    # INSERT
    "INSERT users VALUES (1)",
    "INSERT INTO VALUES (1)",
    "INSERT INTO users (1, 2)",
    "INSERT INTO users VALUES ()",
    "INSERT INTO users VALUES (1 2)",
    "INSERT INTO users VALUES (1, name)",
    "INSERT INTO users VALUES (1, 2",
    "INSERT INTO users VALUES (1) extra",
    # SELECT
    "SELECT FROM users",
    "SELECT * users",
    "SELECT name age FROM users",
    "SELECT *, name FROM users",
    "SELECT * FROM",
    "SELECT * FROM users WHERE",
    "SELECT * FROM users WHERE id 1",
    "SELECT * FROM users WHERE id =",
    "SELECT * FROM users WHERE id = 1 extra",
    # UPDATE
    "UPDATE users age = 1 WHERE id = 1",
    "UPDATE users SET WHERE id = 1",
    "UPDATE users SET age 1 WHERE id = 1",
    "UPDATE users SET age = WHERE id = 1",
    "UPDATE users SET age = 1",
    "UPDATE users SET age = 1, age = 2 WHERE id = 1",
    "UPDATE users SET age = 1 WHERE id = 1 extra",
    # DELETE
    "DELETE users WHERE id = 1",
    "DELETE FROM WHERE id = 1",
    "DELETE FROM users",
    "DELETE FROM users WHERE",
    "DELETE FROM users WHERE id = 1 extra",
])
def test_syntax_errors(sql):
    with pytest.raises(SQLSyntaxError):
        parse(sql)
