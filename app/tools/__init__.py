"""Tool Registry"""

from app.tools.execute_sql import execute_sql
from app.tools.generate_chart import generate_chart
from app.tools.search_arxiv import search_arxiv
from app.tools.search_wikipedia import search_wikipedia
from app.tools.web_search import web_search


RESEARCH_TOOLS = [web_search, search_arxiv, search_wikipedia]

SQL_TOOLS = [execute_sql]

VIZ_TOOLS = [generate_chart]


ALL_TOOLS = [web_search, search_arxiv, search_wikipedia, execute_sql, generate_chart]

_all__ =  ["web_search", "search_arxiv", "search_wikipedia", "execute_sql", "generate_chart",
          "RESEARCH_TOOLS", "VIZ_TOOLS", "ALL_TOOLS", "SQL_TOOLS" ]