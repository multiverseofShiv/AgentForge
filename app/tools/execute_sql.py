from __future__ import annotations

import logging
import re
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text 
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_FORBIDDEN_KEYWORDS = (
    "INSERT","UPDATE","DELETE","DROP","TRUNCATE","ALTER","CREATE","REPLACE","GRANT","REVOKE","ATTACH","DETACH","PRAGMA","VACCUM","REINDEX"
)

_FORBIDDEN_RE = re.compile(
    r"\b("+"|".join(_FORBIDDEN_KEYWORDS)+r")\b",
    re.IGNORECASE,
)
_MULTI_STATEMENT_RE = re.compile(r";\s*\S")

MAX_ROWS = 50

class SQLInput(BaseModel):
    query: str = Field(
        min_length=6,
        max_length=2000,
        description="A single select statement. NO insert/update/delete/ddl"
    )
    
    

def _validate_readonly(query: str)-> str | None:
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return "Empty Query"
    
    
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return "Only Select (or WITH .... SELECT) statements are allowed"
    
    if _FORBIDDEN_RE.search(stripped):
        return (
            "Query Rejected: contains a write/DDL keyword."
            "This tool is strictly read only"
        )
        
    if _MULTI_STATEMENT_RE.search(stripped):
        return "Multiple statements are not allowed - submit one SELECT at a time."
    
    return None



_engine: Engine | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    
    
    settings = get_settings()
    db_path = Path(settings.chinook_db_path).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"Chinook Db not found at {db_path}"
        )
        
    url = f"sqlite:///{db_path.as_posix()}"
    _engine = create_engine(url, future=True)
    return _engine


def _format_rows(columns: list[str], rows: list[tuple]) -> str:
    
    if not rows:
        return f"({','.join(columns)})\n0 rows"
    
    widths = [len(c) for c in columns]
    str_rows = [[("" if v is None else str(v)) for v in r] for r in rows]
    for r in str_rows:
        for i,v in enumerate(r):
            widths[i] = max(widths[i], len(v))
            
            
    def fmt(values: list[str]) -> str:
        return " | ".join(v.ljust(widths[i]) for i,v in enumerate(values))
    
    header = fmt(columns)
    sep = "-+-".join("-" * w for w in widths)
    body = "\n".join(fmt(r) for r in str_rows)
    return f"{header}\n{sep}\n{body}\n({len(rows)}rows)"


@tool(args_schema=SQLInput)
def execute_sql(query: str) -> str:
    """Run a read-only SELECT against the Chinook  SQLite database.
    
    The Chinook schema models a digital media store: artists, albums, tracks, generes, customers, invoices, and employees. Use this when the question can be answered by querying that data (top sellers, revenue by country, track counts per genre, etc.). The tool blocks INSERT/UPDATE/DELETE/DDL. Results are truncated to the first 50 rows.
    """
    
    error = _validate_readonly(query)
    if error:
        return error
    
    
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_ROWS)
            extra = result.fetchone()
            truncated = extra is not None
            
    except FileNotFoundError as exc:
        return str(exc)
    except SQLAlchemyError  as exc:
        logger.exception("Unexpected SQL tool failure")
        return f"SQL tool failed: {exc}"
    except Exception as exc:
        logger.exception("Unexpected SQL tool failure")
        return f"SQL tool failed: {exc}"    
    
    
    output = _format_rows(columns, rows)
    if truncated:
        output += f"\n(Note: result truncated to first {MAX_ROWS} rows.)"
        
    return output




# python -c "from app.tools import execute_sql; print(execute_sql.invoke({'query': 'SELECT Name FROM Artist LIMIT 3'}))"