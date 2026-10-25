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
    web/           Flask web UI (templates/index.html, static/style.css, static/app.js)
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
linedb> SELECT name FROM users WHERE age > 20 ORDER BY age DESC LIMIT 5;
linedb> UPDATE users SET age = 23 WHERE id = 1;
linedb> DELETE FROM users WHERE id = 1;
linedb> DROP TABLE users;
```

Shell commands: `.tables`, `.schema [table]`, `.help`, `exit`.

## Web UI

```
python -m pip install flask            # or: pip install -e ".[web]"
python -m linedb.web [folder]          # then open http://127.0.0.1:5000
```

Browse tables, add / edit / delete rows, create and drop tables, or type
any SQL into the editor (Ctrl+Enter runs it). Every button shows the SQL it
ran. Edit and Delete find a row by its first column, so give each row a
unique first column such as `id`.

The server only listens on 127.0.0.1 because there is no login. Do not run
the web UI and the shell on the same folder at the same time: LineDB has no
file locking between processes.

## Supported SQL

- `CREATE TABLE name (col INT|TEXT, ...)`
- `DROP TABLE name`
- `INSERT INTO name VALUES (value, ...)`
- `SELECT * | col, ... FROM name [WHERE cond] [ORDER BY col [ASC|DESC], ...] [LIMIT n]`
- `UPDATE name SET col = value, ... [WHERE cond]`
- `DELETE FROM name [WHERE cond]`

A condition is `col op value`, where `op` is one of `=`, `!=` (or `<>`),
`<`, `<=`, `>`, `>=`. TEXT values compare alphabetically.
Without a WHERE, UPDATE and DELETE change every row in the table.

## Tests

```
python -m pytest
```
