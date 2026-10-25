import pytest

from linedb import Database, execute


@pytest.fixture
def db(tmp_path):
    """An empty database in a temporary folder."""
    return Database(str(tmp_path))


@pytest.fixture
def users_db(db):
    """A database with a 'users' table holding three rows."""
    execute(db, "CREATE TABLE users (id INT, name TEXT, age INT)")
    execute(db, "INSERT INTO users VALUES (1, 'Kamal', 22)")
    execute(db, "INSERT INTO users VALUES (2, 'Nimali', 25)")
    execute(db, "INSERT INTO users VALUES (3, 'Saman', 22)")
    return db
