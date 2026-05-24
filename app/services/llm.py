import logging
from functools import lru_cache 

from langchain_core.language_models import BaseChatModel


from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
)-> BaseChatModel:
    
    settings = get_settings()
    temp = temperature if temperature is not None else settings.temperature_factual
    mdl = model or settings.supervisor_model
    
    if settings.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            
            return ChatGroq(
                model=mdl,
                temperature= temp,
                api_key=settings.groq_api_key,
            )
        except Exception as exc:
            logger.warning("Chargroq init failed (%s) - falling back to ollama", exc)
            
            
        from langchain_ollama import ChatOllama
        
        ollama_model = ""
        logger.info("Using ChatOllama model=%s temperature=%.1f", ollama_model, temp)
        return ChatOllama(model=ollama_model, temperature= temp)
    
    
@lru_cache(maxsize=4)
def get_cached_llm(temperature: float = 0.0,  model: str = "") -> BaseChatModel:
    return get_llm(temperature=temperature, model=model or None)