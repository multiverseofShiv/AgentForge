from __future__ import annotations

import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    query: str = Field(
        min_length = 2,
        max_length= 200,
        description="Search query - use natural language, be specific"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of results to return (1-10)"
    )
    
def _format_tavily(results: list[dict]) -> str:
    lines: list[str] = []
    for i,r in enumerate(results, start=1):
        title = (r.get("title") or "").strip()
        url = (r.get("href") or r.get("url") or "").strip()
        content = (r.get("content") or "").strip()
        body = (r.get("body") or "").strip()
        lines.append(f"[{i}] {title} \n URL: {url}\n{content}\n")
    return "\n".join(lines).strip() or "No results."
    
    
    
def _format_ddg(results: list[dict]) -> str:
    lines: list[str] = []
    for i,r in enumerate(results, start=1):
        title = (r.get("title") or "").strip()
        url = (r.get("href") or r.get("url") or "").strip()
        content = (r.get("content") or "").strip()
        body = (r.get("body") or "").strip()
        lines.append(f"[{i}] {title} \n URL: {url}\n{content}\n")
    return "\n".join(lines).strip() or "No results."

def _tavily_search(query:str, max_results:int) -> str:
    
    from tavily import TavilyClient
    
    settings = get_settings()
    
    client = TavilyClient(api_key= settings.tavily_api_key)
    
    response = client.search(
        query=query,
        max_results= max_results,
        search_depth="basic",
        include_answer=False,
    )
    return _format_tavily(response.get("results", []))


def ddg_search(query: str, max_results:int)-> str:
    from duckduckgo_search import DDGS
    
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results= max_results))
    return _format_ddg(results)


@tool(args_schema = WebSearchInput)
def web_search(query: str, max_results: int = 5) -> str:
    """Search the live web for recent information.
    
    Use this when the question requires fresh facts, news, current events, or information published after the model's training cutoff.
    Returns a numbered list of results, each with a tittle, URL, and short summary suitable for citation. Prefer `search_wikepedia` for suitable encyclopedic facts and `search_arxiv` for academic papers. 
    """
    
    settings = get_settings()
    
    if settings.tavily_api_key:
        try:
            return _tavily_search(query, max_results)
        except Exception as exc:
            logger.warning("Tavily Search failed, falling back to Duckducko: %s", exc)
            
    try:
        return ddg_search(query, max_results)
    except Exception as exc:
        logger.exception("Duck Duck go search failed")
        return f"web search failed: {exc}"
    
    
    
    
#test
# python -c "from app.tools import web_search; print(web_search.invoke({'query':'Langgraph Supervisor pattern'}))"
# python -c "from app.tools import search_wikipedia; print(search_wikipeia.invoke({'query':'RAG - Retreival Argumentated Generation'}))"
# python -c "from app.tools import search_arxiv; print(search_arxiv.invoke({'query':'mixture of experts routing', 'max_results':2}))"
# python -c "import base64; from app.tools import generate_chart; out = generate_chart.invoke({'chart_type':'bar', 'labels': ['Rock','Jazz', 'Pop'], 'values':[120,45,80], 'title': 'smoke-test'}); open('chart.png','wb').write(base64.b64decode(out.split(',',1)[1]))"
