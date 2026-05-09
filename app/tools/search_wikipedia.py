from __future__ import annotations

import logging


from langchain_core.tools import tool
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

class WikipediaInput(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=200,
        description= "Topic, person, place, concept, - plain English"
    )
    max_results: int = Field(
        default= 2,
        ge = 1,
        le =5,
        description="Number of articles to summarise(1-5)"
    )
    sentences: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Sentences for articke summary (1-15)"
    )
    
    
    
@tool(args_schema= WikipediaInput)
def search_wikipedia(query: str, max_results: int=2, sentences: int =5)-> str :
    """Look up stable encyclopedic background on a topic.
    
    Use this definitions, historical context, biographies, scientific concepts, and other facts unlikely to change week-to-week. Returns one or more article summarises with their canonical wikepedia URL's. Prefer `web_search` for breaking news or recent events
    """
    
    import wikipedia
    
    wikipedia.set_lang("en")
    
    try:
        titles = wikipedia.search(query, results = max_results)
    except Exception as exc:
        logger.exception("wikipedia search failed", exc)
        return f"wikipedia search failed: {exc}"
    if not titles:
        return f"No Wikepedia articles matched '{query}'."
    
    
    chunks: list[str] = []
    for title in titles:
        try: 
            page = wikipedia.page(title, auto_suggest= False, redirect=True)
            summary = wikipedia.summary(
                title, sentences = sentences, auto_suggest = False, redirect = True
            )
            chunks.append(f"## {page.title} \n URL: {page.url}\n {summary}")
        except wikipedia.DisambiguationError as exc:
            options= ", ".join(exc.options[:5])
            chunks.append(f"## {title} \nDiasmbiguation - options:{options}")
        except wikipedia.PageError:
            continue
        except Exception as exc:
            logger.warning("Wikipedia page fetch failed for %s:%s", title, exc)
            continue
        
        return "\n\n".join(chunks) if chunks  else f"No usable wikipedia content for {query}"