import pytest

from linedb import execute


def test_create_and_insert(db):
    assert execute(db, "CREATE TABLE users (id INT, name TEXT, age INT);") == (
        "Table 'users' created"
    )
    assert execute(db, "INSERT INTO users VALUES (1, 'Kamal', 22);") == (
        "1 row inserted"
    )
    assert list(db.table("users").select_all()) == [
        {"id": 1, "name": "Kamal", "age": 22}
    ]


def test_select_all(users_db):
    assert execute(users_db, "SELECT * FROM users") == "\n".join([
        "id | name   | age",
        "---+--------+----",
        "1  | Kamal  | 22",
        "2  | Nimali | 25",
        "3  | Saman  | 22",
        "(3 rows)",
    ])


def test_select_columns_and_where(users_db):
    assert execute(users_db, "SELECT name FROM users WHERE id = 2") == "\n".join([
        "name",
        "------",
        "Nimali",
        "(1 row)",
    ])
    assert execute(users_db, "SELECT * FROM users WHERE age = 22").endswith(
        "(2 rows)"
    )
    assert execute(users_db, "SELECT * FROM users WHERE name = 'Nobody'") == (
        "id | name | age\n---+------+----\n(0 rows)"
    )


def test_update(users_db):
    assert execute(users_db, "UPDATE users SET age = 23 WHERE id = 1") == (
        "1 row updated"
    )
    assert execute(
        users_db, "UPDATE users SET name = 'Sam', age = 40 WHERE id = 3"
    ) == "1 row updated"
    assert execute(users_db, "UPDATE users SET age = 99 WHERE id = 100") == (
        "0 rows updated"
    )
    assert list(users_db.table("users").select_all()) == [
        {"id": 1, "name": "Kamal", "age": 23},
        {"id": 2, "name": "Nimali", "age": 25},
        {"id": 3, "name": "Sam", "age": 40},
    ]


def test_delete(users_db):
    assert execute(users_db, "DELETE FROM users WHERE age = 22") == (
        "2 rows deleted"
    )
    assert execute(users_db, "DELETE FROM users WHERE id = 100") == (
        "0 rows deleted"
    )
    assert [r["id"] for r in users_db.table("users").select_all()] == [2]


@pytest.mark.parametrize("sql", [
    # INSERT
    "INSERT INTO users VALUES ('abc', 'Bad', 20)",
    "INSERT INTO users VALUES (4, 'Short')",
    "INSERT INTO nothing VALUES (1)",
    # SELECT
    "SELECT height FROM users",
    "SELECT * FROM users WHERE height = 1",
    "SELECT * FROM users WHERE id = 'abc'",
    "SELECT * FROM nothing",
    # UPDATE
    "UPDATE users SET height = 1 WHERE id = 1",
    "UPDATE users SET age = 'old' WHERE id = 1",
    "UPDATE users SET age = 1 WHERE id = 'abc'",
    "UPDATE users SET age = 1 WHERE height = 1",
    "UPDATE nothing SET age = 1 WHERE id = 1",
    # DELETE
    "DELETE FROM users WHERE id = 'abc'",
    "DELETE FROM users WHERE height = 1",
    "DELETE FROM nothing WHERE id = 1",
])
def test_database_errors(users_db, sql):
    with pytest.raises(ValueError):
        execute(users_db, sql)
