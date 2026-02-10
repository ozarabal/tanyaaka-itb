from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_NAME: str = "TanyaAka-ITB"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: Union[list[str], str] = '["http://localhost:5173"]'

    # LLM Provider: "openai" or "azure"
    LLM_PROVIDER: str = "openai"

    # OpenAI (alternative for local dev)
    OPENAI_API_KEY: Optional[str] = None

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "itb_regulations"

    # RAG
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVER_TOP_K: int = 7

    # PDF source directory
    PDF_DIR: str = "./data/pdfs"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from environment variable."""
        if isinstance(v, str):
            # Remove any whitespace
            v = v.strip()
            
            # Try to parse as JSON first
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            
            # If comma-separated, split it
            if "," in v:
                return [origin.strip() for origin in v.split(",")]
            
            # Single origin
            if v:
                return [v]
            
            # Empty string, return default
            return ["http://localhost:5173"]
        
        # Already a list
        return v


settings = Settings()