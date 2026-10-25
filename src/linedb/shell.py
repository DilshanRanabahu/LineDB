import sys

from .executor import execute
from .storage import Database

PROMPT = "linedb> "
CONTINUE_PROMPT = "   ...> "

HELP = """\
Type SQL ending with ';'. A statement can span several lines.

  .tables           list all tables
  .schema [table]   show the CREATE TABLE statement(s)
  .help             show this help
  exit              leave the shell (Ctrl+C clears the current input)"""


def split_statements(text):
    """Cut text into complete statements (each ending in ';') and a leftover.

    A ';' inside a 'quoted string' does not end a statement.
    """
    statements = []
    start = 0
    in_string = False
    for i, ch in enumerate(text):
        if ch == "'":
            in_string = not in_string      # '' toggles twice, so it is fine
        elif ch == ";" and not in_string:
            statements.append(text[start:i + 1])
            start = i + 1
    return statements, text[start:]


def schema_text(table):
    columns = ", ".join(
        f"{name} {type_name}" for name, type_name in table.schema.items()
    )
    return f"CREATE TABLE {table.name} ({columns});"


def handle_command(db, line):
    """Run a dot command. Returns False when the shell should exit."""
    parts = line.split()
    command = parts[0].lower()

    if command in (".exit", ".quit"):
        return False
    if command == ".help":
        print(HELP)
    elif command == ".tables":
        for name in sorted(db.tables):
            print(name)
    elif command == ".schema":
        for name in parts[1:] or sorted(db.tables):
            try:
                print(schema_text(db.table(name)))
            except ValueError as e:
                print(f"Error: {e}")
    else:
        print(f"Unknown command: {parts[0]} (try .help)")
    return True


def run_shell(db):
    print("LineDB shell. Type .help for help, exit to quit.")
    buffer = ""

    while True:
        try:
            line = input(CONTINUE_PROMPT if buffer else PROMPT)
        except EOFError:                    # Ctrl+Z then Enter (Ctrl+D on Linux)
            print()
            break
        except KeyboardInterrupt:           # Ctrl+C: throw away what was typed
            print("^C")
            buffer = ""
            continue

        # commands are only understood at the start of a new statement
        if not buffer:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower() in ("exit", "quit"):
                break
            if stripped.startswith("."):
                if not handle_command(db, stripped):
                    break
                continue

        buffer += line + "\n"
        statements, buffer = split_statements(buffer)
        if not buffer.strip():
            buffer = ""

        for statement in statements:
            if statement.strip() == ";":
                continue
            try:
                print(execute(db, statement))
            except ValueError as e:         # includes SQLSyntaxError
                print(f"Error: {e}")
            except Exception as e:          # a bug in our code: do not crash
                print(f"Internal error: {type(e).__name__}: {e}")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "db_data"
    run_shell(Database(folder))


if __name__ == "__main__":
    main()