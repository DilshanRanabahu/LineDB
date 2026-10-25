import pytest

from linedb import Result, execute, run


def test_run_returns_data(users_db):
    assert run(users_db, "SELECT name FROM users WHERE age = 22") == Result(
        "2 rows", columns=["name"], rows=[["Kamal"], ["Saman"]]
    )
    assert run(users_db, "DELETE FROM users WHERE id = 1") == Result(
        "1 row deleted"
    )


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


def first_column(db, sql):
    """Run a SELECT and return the first column of the result as strings."""
    lines = execute(db, sql).split("\n")
    body = lines[2:-1]          # skip header, separator line and row count
    return [line.split("|")[0].strip() for line in body]


@pytest.mark.parametrize("where, names", [
    ("age = 22", ["Kamal", "Saman"]),
    ("age != 22", ["Nimali"]),
    ("age <> 22", ["Nimali"]),
    ("age < 25", ["Kamal", "Saman"]),
    ("age <= 25", ["Kamal", "Nimali", "Saman"]),
    ("age > 22", ["Nimali"]),
    ("age >= 25", ["Nimali"]),
    ("name < 'N'", ["Kamal"]),
    ("id > 100", []),
])
def test_select_where_operators(users_db, where, names):
    assert first_column(users_db, f"SELECT name FROM users WHERE {where}") == (
        names
    )


@pytest.mark.parametrize("clause, names", [
    ("ORDER BY name", ["Kamal", "Nimali", "Saman"]),
    ("ORDER BY name DESC", ["Saman", "Nimali", "Kamal"]),
    ("ORDER BY age", ["Kamal", "Saman", "Nimali"]),      # ties keep file order
    ("ORDER BY age DESC, name", ["Nimali", "Kamal", "Saman"]),
    ("ORDER BY age, name DESC", ["Saman", "Kamal", "Nimali"]),
    ("LIMIT 2", ["Kamal", "Nimali"]),
    ("LIMIT 0", []),
    ("LIMIT 100", ["Kamal", "Nimali", "Saman"]),
    ("ORDER BY id DESC LIMIT 1", ["Saman"]),
    ("WHERE age = 22 ORDER BY name DESC LIMIT 1", ["Saman"]),
])
def test_select_order_by_and_limit(users_db, clause, names):
    assert first_column(users_db, f"SELECT name FROM users {clause}") == names


def test_order_by_a_column_that_is_not_shown(users_db):
    assert first_column(users_db, "SELECT name FROM users ORDER BY age DESC") == [
        "Nimali", "Kamal", "Saman"
    ]


def test_update_and_delete_with_operators(users_db):
    assert execute(users_db, "UPDATE users SET age = 30 WHERE age < 25") == (
        "2 rows updated"
    )
    assert execute(users_db, "DELETE FROM users WHERE name != 'Kamal'") == (
        "2 rows deleted"
    )
    assert list(users_db.table("users").select_all()) == [
        {"id": 1, "name": "Kamal", "age": 30}
    ]


def test_update_every_row(users_db):
    assert execute(users_db, "UPDATE users SET age = 0") == "3 rows updated"
    assert first_column(users_db, "SELECT age FROM users") == ["0", "0", "0"]


def test_delete_every_row(users_db):
    assert execute(users_db, "DELETE FROM users;") == "3 rows deleted"
    assert execute(users_db, "SELECT * FROM users").endswith("(0 rows)")
    # the table itself is still there and usable
    assert execute(users_db, "INSERT INTO users VALUES (9, 'New', 1)") == (
        "1 row inserted"
    )


def test_drop_table(users_db):
    assert execute(users_db, "DROP TABLE users;") == "Table 'users' dropped"
    with pytest.raises(ValueError, match="No such table"):
        execute(users_db, "SELECT * FROM users")
    with pytest.raises(ValueError, match="No such table"):
        execute(users_db, "DROP TABLE users")

    # create it again: it starts empty
    execute(users_db, "CREATE TABLE users (id INT)")
    assert execute(users_db, "SELECT * FROM users").endswith("(0 rows)")


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
    "SELECT * FROM users WHERE age > 'old'",
    "SELECT * FROM users ORDER BY height",
    # UPDATE
    "UPDATE users SET height = 1 WHERE id = 1",
    "UPDATE users SET age = 'old' WHERE id = 1",
    "UPDATE users SET age = 1 WHERE id = 'abc'",
    "UPDATE users SET age = 1 WHERE height = 1",
    "UPDATE nothing SET age = 1 WHERE id = 1",
    "UPDATE users SET age = 'old'",
    "UPDATE users SET age = 1 WHERE id < 'abc'",
    # DELETE
    "DELETE FROM users WHERE id = 'abc'",
    "DELETE FROM users WHERE height = 1",
    "DELETE FROM nothing WHERE id = 1",
    "DELETE FROM nothing",
    "DELETE FROM users WHERE id >= 'abc'",
    # DROP TABLE
    "DROP TABLE nothing",
])
def test_database_errors(users_db, sql):
    with pytest.raises(ValueError):
        execute(users_db, sql)
