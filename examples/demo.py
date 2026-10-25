"""Use the storage engine directly from Python, without SQL.

Run from the project root:  python examples/demo.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from linedb import Database  # noqa: E402

FOLDER = "data"

# start fresh on every test run
if os.path.exists(FOLDER):
    shutil.rmtree(FOLDER)

# --- first "program run": create the table and add data ---
db = Database(FOLDER)
users = db.create_table("users", {"id": "INT", "name": "TEXT", "age": "INT"})
users.insert({"id": 1, "name": "Kamal", "age": 22})
users.insert({"id": 2, "name": "Nimali", "age": 25})
print("tables:", list(db.tables))

# type checks
try:
    users.insert({"id": "abc", "name": "Bad", "age": 20})
except ValueError as e:
    print("type check works:", e)
try:
    db.create_table("users", {"id": "INT"})
except ValueError as e:
    print("duplicate table check works:", e)
try:
    db.create_table("things", {"id": "FLOATY"})
except ValueError as e:
    print("unknown type check works:", e)

# --- second "program run": open the same folder again ---
db2 = Database(FOLDER)
users2 = db2.table("users")
print("schema after reopen:", users2.schema)
print("rows after reopen:", list(users2.select_all()))

print("updated:", users2.update({"age": 23}, ("name", "=", "Kamal")))
print("deleted:", users2.delete(("id", "=", 2)))
print("final rows:", list(users2.select_all()))