from .errors import SQLSyntaxError
from .storage import TYPES

KEYWORDS = {
    "CREATE", "TABLE", "INSERT", "INTO", "VALUES",
    "SELECT", "FROM", "WHERE", "UPDATE", "SET", "DELETE", "DROP",
    "ORDER", "BY", "ASC", "DESC", "LIMIT",
} | set(TYPES)      # type names (INT, TEXT) are keywords too

SYMBOLS = set("(),*=;<>")

# two-character operators; '<>' is another way to write '!='
TWO_CHAR_SYMBOLS = {"!=": "!=", "<>": "!=", "<=": "<=", ">=": ">="}


def tokenize(sql):
    """Split an SQL string into a list of (kind, value) tokens.

    kind is one of: KEYWORD, IDENT, NUMBER, STRING, SYMBOL
    """
    tokens = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        # 1. skip spaces, tabs, newlines
        if ch.isspace():
            i += 1
            continue

        # 2. two-character operators: != <> <= >=
        pair = sql[i:i + 2]
        if pair in TWO_CHAR_SYMBOLS:
            tokens.append(("SYMBOL", TWO_CHAR_SYMBOLS[pair]))
            i += 2
            continue

        # 3. single-character symbols: ( ) , * = ; < >
        if ch in SYMBOLS:
            tokens.append(("SYMBOL", ch))
            i += 1
            continue

        # 4. string literal: 'Kamal'  (a doubled '' inside means one quote)
        if ch == "'":
            start = i
            i += 1
            chars = []
            while True:
                if i >= n:
                    raise SQLSyntaxError(
                        f"Unterminated string starting at position {start}"
                    )
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        chars.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(sql[i])
                i += 1
            tokens.append(("STRING", "".join(chars)))
            continue

        # 5. number: 22 or -5
        if ch.isdigit() or (ch == "-" and i + 1 < n and sql[i + 1].isdigit()):
            start = i
            i += 1
            while i < n and sql[i].isdigit():
                i += 1
            tokens.append(("NUMBER", int(sql[start:i])))
            continue

        # 6. word: keyword (SELECT) or identifier (users, name)
        if ch.isalpha() or ch == "_":
            start = i
            while i < n and (sql[i].isalnum() or sql[i] == "_"):
                i += 1
            word = sql[start:i]
            if word.upper() in KEYWORDS:
                tokens.append(("KEYWORD", word.upper()))
            else:
                tokens.append(("IDENT", word))
            continue

        # 7. anything else is not valid SQL for us
        raise SQLSyntaxError(f"Unexpected character {ch!r} at position {i}")

    return tokens