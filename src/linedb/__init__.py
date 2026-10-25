"""LineDB: a tiny SQL database that stores each table as a JSON Lines file."""

from .errors import SQLSyntaxError
from .executor import Result, execute, run
from .parser import parse
from .storage import Database, Table

__all__ = [
    "Database", "Table", "Result", "SQLSyntaxError", "execute", "parse", "run",
]
__version__ = "0.1.0"
