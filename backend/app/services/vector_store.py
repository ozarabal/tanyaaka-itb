from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain.schema import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    def __init__(self):
        self._embeddings = self._create_embeddings()
        self._store: Chroma | None = None

    def _create_embeddings(self):
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    @property
    def store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=self._embeddings,
                persist_directory=settings.CHROMA_PERSIST_DIR,
            )
            logger.info("chroma_initialized", persist_dir=settings.CHROMA_PERSIST_DIR)
        return self._store

    def add_documents(self, documents: list[Document]) -> int:
        """Add document chunks to the vector store. Returns count added."""
        self.store.add_documents(documents)
        count = len(documents)
        logger.info("documents_added", count=count)
        return count

    def similarity_search(
        self, query: str, k: int = settings.RETRIEVER_TOP_K
    ) -> list[Document]:
        """Search for similar documents."""
        results = self.store.similarity_search(query, k=k)
        logger.info("similarity_search", query_length=len(query), results=len(results))
        return results

    def get_retriever(self, k: int = settings.RETRIEVER_TOP_K):
        """Return a LangChain retriever interface for use in chains."""
        return self.store.as_retriever(search_kwargs={"k": k})

    def list_documents(self) -> dict[str, int]:
        """Return a mapping of filename -> chunk count from the store."""
        collection = self.store._collection
        result = collection.get(include=["metadatas"])
        doc_counts: dict[str, int] = {}
        if result and result["metadatas"]:
            for meta in result["metadatas"]:
                fname = meta.get("source_filename", "unknown")
                doc_counts[fname] = doc_counts.get(fname, 0) + 1
        return doc_counts

    @property
    def is_ready(self) -> bool:
        try:
            count = self.store._collection.count()
            return count > 0
        except Exception:
            return False


vector_store_service = VectorStoreService()
