import pytest

from linedb import Database


@pytest.fixture
def users(db):
    table = db.create_table("users", {"id": "INT", "name": "TEXT", "age": "INT"})
    table.insert({"id": 1, "name": "Kamal", "age": 22})
    table.insert({"id": 2, "name": "Nimali", "age": 25})
    return table


def test_data_survives_reopen(db, users):
    reopened = Database(db.folder).table("users")
    assert reopened.schema == {"id": "INT", "name": "TEXT", "age": "INT"}
    assert list(reopened.select_all()) == [
        {"id": 1, "name": "Kamal", "age": 22},
        {"id": 2, "name": "Nimali", "age": 25},
    ]


def test_insert_keeps_schema_column_order(users):
    users.insert({"age": 30, "name": "Saman", "id": 3})
    assert list(list(users.select_all())[-1]) == ["id", "name", "age"]


def test_update_and_delete(users):
    assert users.update("name", "Kamal", {"age": 23}) == 1
    assert users.delete("id", 2) == 1
    assert list(users.select_all()) == [{"id": 1, "name": "Kamal", "age": 23}]


@pytest.mark.parametrize("row", [
    {"id": "abc", "name": "Bad", "age": 20},    # wrong type
    {"id": True, "name": "Bad", "age": 20},     # bool is not an INT
    {"id": 3, "name": "Short"},                 # missing column
])
def test_insert_rejects_bad_rows(users, row):
    with pytest.raises(ValueError):
        users.insert(row)


def test_create_table_errors(db, users):
    with pytest.raises(ValueError, match="already exists"):
        db.create_table("users", {"id": "INT"})
    with pytest.raises(ValueError, match="Unknown type"):
        db.create_table("things", {"id": "FLOATY"})
    with pytest.raises(ValueError, match="Invalid table name"):
        db.create_table("../evil", {"id": "INT"})
    with pytest.raises(ValueError, match="at least one column"):
        db.create_table("empty", {})


def test_corrupt_line_is_skipped_and_kept(users):
    with open(users.path, "a", encoding="utf-8") as f:
        f.write('{"id": 9, "na')     # a write that was cut off
    assert len(list(users.select_all())) == 2

    # the next insert starts on a fresh line, and rewrites keep the bad line
    users.insert({"id": 3, "name": "Saman", "age": 30})
    users.delete("id", 1)
    assert [r["id"] for r in users.select_all()] == [2, 3]
    with open(users.path, encoding="utf-8") as f:
        assert '{"id": 9, "na\n' in f.read()
