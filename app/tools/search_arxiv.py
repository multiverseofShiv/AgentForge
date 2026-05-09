from __future__ import annotations

import logging

from langchain_core.tools import tool 
from pydantic import BaseModel, Field

logger = logging.getLogger("__name__")

class ArxivInput(BaseModel):
    query: str =Field(
        min_length=2,
        max_length=300,
        description="Topic or keywords. Free Text academic query."
    )
    max_results: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of papers to return (1-10)."
    )
    
    
@tool(args_schema=ArxivInput)
def arxiv_search(query: str, max_results: int = 3) -> str:
    """Search arxiv for academic papers on a research topic.
    
    Use this when the question is technical or scientific and credible papers would stengthen the answer. Returns the title, authors, publication date, abstract, and arXiv URL for each paper. Not suitable for general-purpose questions - prefer 'web_search' or 'search_wikipedia for those."""
    
    import arxiv
    
    try:
        search = arxiv.Search(
            query=query,
            max_results= max_results,
            sort_by= arxiv.SortCriterion.Relevance,
        )
        results = list(search.results())
    except Exception as exc:
        logger.exception("arxiv Search failed")
        return f"arxiv Search failed : {exc}"
    
    if not results:
        return f"No arXiv papers matched '{query}'"
    
    chunks: list[str] = []
    for i, paper in enumerate(results, start=1):
        authors = ",".join(a.name for a in paper.authors[:5])
        if len(paper.authors)>5:
            authors +=f",+{len(paper.authors)-5} more"
            
        published = paper.published.date().isoformat() if  paper.puq else "n/a"
        
        abstract = (paper.summary or "").strip().replace("\n"," ")
        chunks.append(
            f"[{i}] {paper.title}\n"
            f"Authors: {authors} \n"
            f"Published: {published}\n"
            f"URL: {paper.entry_id}\n"
            f"Abstract: {abstract}"
            )
    
    return "\n\n".join(chunks)