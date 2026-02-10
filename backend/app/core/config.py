from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

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
    RETRIEVER_TOP_K: int = 4

    # PDF source directory
    PDF_DIR: str = "./data/pdfs"


settings = Settings()
