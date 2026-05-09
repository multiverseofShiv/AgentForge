from functools import lru_cache 
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    groq_api_key: str = ""
    
    
    tavily_api_key: str = ""
    
    
    langfuse_public_key: str =""
    langfuse_secret_key: str =""
    langfuse_host: str= ""
    
    huggingface_token: str = ""
    supervisor_model: str = "llama"
    temperature_factual: float= 0.0
    temperature_creative: float = 0.0
    
    app_env: str = "developent"
    log_level: str = "INFO"
    
    
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()