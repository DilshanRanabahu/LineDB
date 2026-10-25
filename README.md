# LineDB

A tiny SQL database written from scratch in Python, with no dependencies.
Each table is stored as a JSON Lines file (one row per line), and the table
schemas live in `catalog.json`.

## Project layout

```
src/linedb/
    storage.py     Database and Table: files on disk, type checks, atomic rewrites
    tokenizer.py   SQL text -> tokens
    parser.py      tokens -> statement dict
    executor.py    runs a statement against a Database
    shell.py       interactive linedb> prompt
    errors.py      SQLSyntaxError
tests/             pytest test suite
examples/demo.py   using the storage engine directly from Python
```

## Usage

```
python -m pip install -e ".[dev]"   # optional: installs the `linedb` command and pytest
python -m linedb [folder]           # start the shell (default folder: db_data)
```

Without installing, run `python -m linedb` from the `src` folder.

```
linedb> CREATE TABLE users (id INT, name TEXT, age INT);
linedb> INSERT INTO users VALUES (1, 'Kamal', 22);
linedb> SELECT name FROM users WHERE id = 1;
linedb> UPDATE users SET age = 23 WHERE id = 1;
linedb> DELETE FROM users WHERE id = 1;
```

Shell commands: `.tables`, `.schema [table]`, `.help`, `exit`.

## Supported SQL

- `CREATE TABLE name (col INT|TEXT, ...)`
- `INSERT INTO name VALUES (value, ...)`
- `SELECT * | col, ... FROM name [WHERE col = value]`
- `UPDATE name SET col = value, ... WHERE col = value`
- `DELETE FROM name WHERE col = value`

## Tests

```
python -m pytest
```
