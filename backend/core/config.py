import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration system."""
    project_name: str = "RescueNet AI"
    version: str = "2.0.0"
    
    # Infrastructure
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./rescuenet.db")
    
    # LLM Settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    default_model: str = "gpt-4o"
    
    # Execution Settings
    max_retries: int = 3
    timeout_ms: int = 5000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
