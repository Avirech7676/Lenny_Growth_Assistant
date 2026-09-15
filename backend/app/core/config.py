from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "The Lenny Growth Assistant"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    POSTGRES_USER: str = "lenny_user"
    POSTGRES_PASSWORD: str = "lenny_secure_password_2026"
    POSTGRES_DB: str = "lenny_growth_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # LLM Settings
    LLM_PROVIDER: str = "auto"  # "auto" | "ollama" | "anthropic" | "openai" | "gemini" | "groq"
    MODEL: Optional[str] = "AUTO"  # "AUTO" | provider or model identifier
    MODEL_ROUTER_MODE: str = "auto"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text:latest"

    # Cloud Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Epistemic Grounding Parameters
    COSINE_SIMILARITY_THRESHOLD: float = 0.65
    TOP_K_CHUNKS: int = 4

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
