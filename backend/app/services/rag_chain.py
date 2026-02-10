from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import Document

from app.core.config import settings
from app.core.logging import get_logger
from app.services.vector_store import vector_store_service

logger = get_logger(__name__)

SYSTEM_PROMPT = """Kamu adalah asisten akademik untuk Institut Teknologi Bandung (ITB).
Tugasmu adalah menjawab pertanyaan tentang peraturan akademik berdasarkan konteks yang diberikan.

Aturan:
1. Jawab HANYA berdasarkan konteks yang diberikan. Jika informasi tidak ada di konteks, katakan bahwa kamu tidak menemukan informasi tersebut.
2. Jawab dalam bahasa yang sama dengan pertanyaan (Indonesia atau Inggris).
3. Sebutkan sumber dokumen yang relevan di akhir jawaban.
4. Berikan jawaban yang ringkas dan jelas.

Konteks:
{context}
"""

USER_PROMPT = "{question}"


def _create_llm():
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1,
        max_tokens=1024,
    )


def _format_docs(docs: list[Document]) -> str:
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_filename", "unknown")
        page = doc.metadata.get("page", "?")
        formatted.append(f"[Sumber {i}: {source}, Halaman {page}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


class RAGChain:
    def __init__(self):
        self._llm = _create_llm()
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    async def query(self, question: str) -> dict:
        """Execute RAG query. Returns dict with 'answer', 'sources', 'model'."""
        retriever = vector_store_service.get_retriever()
        docs = retriever.invoke(question)

        logger.info("rag_retrieve", question_length=len(question), docs_found=len(docs))

        context = _format_docs(docs)

        chain = self._prompt | self._llm | StrOutputParser()
        answer = await chain.ainvoke({"context": context, "question": question})

        sources = []
        for doc in docs:
            sources.append({
                "document": doc.metadata.get("source_filename", "unknown"),
                "page": doc.metadata.get("page"),
                "content_snippet": doc.page_content[:200],
            })

        model_name = ("gpt-3.5-turbo")

        return {
            "answer": answer,
            "sources": sources,
            "model": model_name,
        }


rag_chain = RAGChain()
