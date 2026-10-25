from .errors import SQLSyntaxError
from .storage import TYPES
from .tokenizer import tokenize


class Parser:
    """Turns a list of tokens into a statement dictionary."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0    # index of the next token to look at

    # ---------- small helpers ----------

    def peek(self):
        """Look at the next token without using it up."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ("EOF", None)

    def next(self):
        """Take the next token and move forward."""
        token = self.peek()
        self.pos += 1
        return token

    def expect_keyword(self, word):
        kind, value = self.next()
        if kind != "KEYWORD" or value != word:
            raise SQLSyntaxError(f"Expected {word}, got {self._show(kind, value)}")

    def expect_symbol(self, symbol):
        kind, value = self.next()
        if kind != "SYMBOL" or value != symbol:
            raise SQLSyntaxError(
                f"Expected '{symbol}', got {self._show(kind, value)}"
            )

    def expect_ident(self, what):
        kind, value = self.next()
        if kind != "IDENT":
            raise SQLSyntaxError(f"Expected {what}, got {self._show(kind, value)}")
        return value

    @staticmethod
    def _show(kind, value):
        return "end of input" if kind == "EOF" else repr(value)

    def parse_value(self):
        """A literal value: a number or a 'text' string."""
        kind, value = self.next()
        if kind in ("NUMBER", "STRING"):
            return value
        raise SQLSyntaxError(
            f"Expected a value (number or 'text'), got {self._show(kind, value)}"
        )

    # ---------- statements ----------

    def parse(self):
        kind, value = self.peek()
        if kind == "EOF":
            raise SQLSyntaxError("Empty statement")

        if (kind, value) == ("KEYWORD", "CREATE"):
            statement = self.parse_create_table()
        elif (kind, value) == ("KEYWORD", "INSERT"):
            statement = self.parse_insert()
        elif (kind, value) == ("KEYWORD", "SELECT"):
            statement = self.parse_select()
        elif (kind, value) == ("KEYWORD", "UPDATE"):
            statement = self.parse_update()
        elif (kind, value) == ("KEYWORD", "DELETE"):
            statement = self.parse_delete()
        else:
            raise SQLSyntaxError(f"Unsupported statement: {value!r}")

        # an optional ';' at the end, then nothing else is allowed
        if self.peek() == ("SYMBOL", ";"):
            self.next()
        if self.peek()[0] != "EOF":
            raise SQLSyntaxError(
                f"Unexpected extra input: {self._show(*self.peek())}"
            )
        return statement

    def parse_create_table(self):
        # CREATE TABLE name ( col TYPE , col TYPE , ... )
        self.expect_keyword("CREATE")
        self.expect_keyword("TABLE")
        table = self.expect_ident("a table name")
        self.expect_symbol("(")

        columns = {}
        while True:
            column = self.expect_ident("a column name")
            if column in columns:
                raise SQLSyntaxError(f"Duplicate column name: {column}")

            kind, value = self.next()
            if kind != "KEYWORD" or value not in TYPES:
                raise SQLSyntaxError(
                    f"Expected a column type ({' or '.join(TYPES)}), got "
                    f"{self._show(kind, value)}"
                )
            columns[column] = value

            kind, value = self.next()
            if (kind, value) == ("SYMBOL", ","):
                continue            # another column follows
            if (kind, value) == ("SYMBOL", ")"):
                break               # end of the column list
            raise SQLSyntaxError(
                f"Expected ',' or ')', got {self._show(kind, value)}"
            )

        return {"type": "create_table", "table": table, "columns": columns}

    def parse_insert(self):
        # INSERT INTO name VALUES ( value , value , ... )
        self.expect_keyword("INSERT")
        self.expect_keyword("INTO")
        table = self.expect_ident("a table name")
        self.expect_keyword("VALUES")
        self.expect_symbol("(")

        values = []
        while True:
            values.append(self.parse_value())

            kind, value = self.next()
            if (kind, value) == ("SYMBOL", ","):
                continue            # another value follows
            if (kind, value) == ("SYMBOL", ")"):
                break               # end of the value list
            raise SQLSyntaxError(
                f"Expected ',' or ')', got {self._show(kind, value)}"
            )

        return {"type": "insert", "table": table, "values": values}

    def parse_select(self):
        # SELECT * FROM name [WHERE column = value]
        # SELECT col, col FROM name [WHERE column = value]
        self.expect_keyword("SELECT")

        if self.peek() == ("SYMBOL", "*"):
            self.next()
            columns = None              # None means "all columns"
        else:
            columns = []
            while True:
                columns.append(self.expect_ident("a column name"))
                if self.peek() == ("SYMBOL", ","):
                    self.next()
                    continue            # another column follows
                break

        self.expect_keyword("FROM")
        table = self.expect_ident("a table name")

        where = None
        if self.peek() == ("KEYWORD", "WHERE"):
            self.next()
            where = self.parse_where()

        return {"type": "select", "table": table, "columns": columns,
                "where": where}

    def parse_update(self):
        # UPDATE name SET col = value [, col = value ...] WHERE column = value
        self.expect_keyword("UPDATE")
        table = self.expect_ident("a table name")
        self.expect_keyword("SET")

        changes = {}
        while True:
            column = self.expect_ident("a column name")
            if column in changes:
                raise SQLSyntaxError(f"Column set twice: {column}")
            self.expect_symbol("=")
            changes[column] = self.parse_value()

            if self.peek() == ("SYMBOL", ","):
                self.next()
                continue            # another assignment follows
            break

        if self.peek() != ("KEYWORD", "WHERE"):
            raise SQLSyntaxError(
                "UPDATE needs a WHERE clause (updating every row is not "
                "supported yet)"
            )
        self.next()
        where = self.parse_where()

        return {"type": "update", "table": table, "changes": changes,
                "where": where}

    def parse_delete(self):
        # DELETE FROM name WHERE column = value
        self.expect_keyword("DELETE")
        self.expect_keyword("FROM")
        table = self.expect_ident("a table name")

        if self.peek() != ("KEYWORD", "WHERE"):
            raise SQLSyntaxError(
                "DELETE needs a WHERE clause (deleting every row is not "
                "supported yet)"
            )
        self.next()
        where = self.parse_where()

        return {"type": "delete", "table": table, "where": where}

    def parse_where(self):
        # column = value
        column = self.expect_ident("a column name")
        self.expect_symbol("=")
        value = self.parse_value()
        return {"column": column, "value": value}


def parse(sql):
    """SQL text in, statement dictionary out."""
    return Parser(tokenize(sql)).parse()