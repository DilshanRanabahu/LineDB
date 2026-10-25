import pytest

from linedb.errors import SQLSyntaxError
from linedb.tokenizer import tokenize


def test_create_table_tokens():
    assert tokenize("CREATE TABLE users (id INT, name TEXT);") == [
        ("KEYWORD", "CREATE"), ("KEYWORD", "TABLE"), ("IDENT", "users"),
        ("SYMBOL", "("), ("IDENT", "id"), ("KEYWORD", "INT"), ("SYMBOL", ","),
        ("IDENT", "name"), ("KEYWORD", "TEXT"), ("SYMBOL", ")"),
        ("SYMBOL", ";"),
    ]


def test_keywords_are_case_insensitive():
    assert tokenize("select") == [("KEYWORD", "SELECT")]


def test_identifiers_keep_their_case():
    assert tokenize("Users") == [("IDENT", "Users")]


def test_doubled_quote_inside_string():
    assert tokenize("'a''b'") == [("STRING", "a'b")]


def test_negative_number():
    assert tokenize("-12") == [("NUMBER", -12)]
    assert tokenize("age = -5") == [
        ("IDENT", "age"), ("SYMBOL", "="), ("NUMBER", -5),
    ]


def test_comparison_operators():
    assert tokenize("= != <> < <= > >=") == [
        ("SYMBOL", "="), ("SYMBOL", "!="), ("SYMBOL", "!="), ("SYMBOL", "<"),
        ("SYMBOL", "<="), ("SYMBOL", ">"), ("SYMBOL", ">="),
    ]
    # no spaces needed, and a negative number right after an operator
    assert tokenize("age>=-5") == [
        ("IDENT", "age"), ("SYMBOL", ">="), ("NUMBER", -5),
    ]


def test_new_keywords():
    assert tokenize("drop order by asc desc limit") == [
        ("KEYWORD", word)
        for word in ["DROP", "ORDER", "BY", "ASC", "DESC", "LIMIT"]
    ]


@pytest.mark.parametrize("sql, message", [
    ("SELECT # FROM users", "Unexpected character '#'"),
    ("SELECT * FROM users WHERE id ! 1", "Unexpected character '!'"),
    ("INSERT INTO users VALUES ('abc", "Unterminated string"),
])
def test_errors(sql, message):
    with pytest.raises(SQLSyntaxError, match=message):
        tokenize(sql)
