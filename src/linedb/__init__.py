"""LineDB: a tiny SQL database that stores each table as a JSON Lines file."""

from .errors import SQLSyntaxError
from .executor import execute
from .parser import parse
from .storage import Database, Table

__all__ = ["Database", "Table", "SQLSyntaxError", "execute", "parse"]
__version__ = "0.1.0"
