"""Standard RAG — ChromaDB + Google Gemini embeddings (the baseline approach)."""

import time
import os
from typing import List, Dict, Any

from src.config import Config
from src.pdf_loader import Document


def _get_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model=Config.GEMINI_EMBEDDING_MODEL,
        google_api_key=Config.GEMINI_API_KEY,
    )


def _get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0,
    )


def _get_vectorstore(embeddings):
    from langchain_community.vectorstores import Chroma
    os.makedirs(Config.CHROMA_DIR, exist_ok=True)
    return Chroma(
        persist_directory=Config.CHROMA_DIR,
        embedding_function=embeddings,
    )


class StandardRAG:
    """
    Standard RAG — the 'Filing Cabinet' approach.

    How it works:
      1. INGEST: Split docs into chunks → embed each chunk → store vectors in ChromaDB
      2. QUERY:  Embed the question → find most similar chunks → pass to LLM → answer

    Limitation: Treats knowledge as isolated text chunks.
    No understanding of relationships between entities or global themes.
    """

    def __init__(self):
        Config.validate()
        self._embeddings = None
        self._vectorstore = None
        self._llm = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        return self._embeddings

    @property
    def vectorstore(self):
        if self._vectorstore is None:
            self._vectorstore = _get_vectorstore(self.embeddings)
        return self._vectorstore

    @property
    def llm(self):
        if self._llm is None:
            self._llm = _get_llm()
        return self._llm

    def ingest(self, documents: List[Document]) -> int:
        """Embed and store documents in ChromaDB."""
        from langchain_core.documents import Document as LCDocument

        lc_docs = [
            LCDocument(
                page_content=doc.page_content,
                metadata=doc.metadata,
            )
            for doc in documents
        ]

        # Add in batches to avoid rate limits
        batch_size = 50
        total = 0
        for i in range(0, len(lc_docs), batch_size):
            batch = lc_docs[i : i + batch_size]
            self.vectorstore.add_documents(batch)
            total += len(batch)
            print(f"    Standard RAG: ingested {total}/{len(lc_docs)} chunks...")
            time.sleep(0.5)  # avoid embedding rate limits

        return total

    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant chunks and generate an answer.

        Returns dict with: answer, sources, latency_ms, chunks_used, method
        """
        start = time.time()

        # Retrieve top-k similar chunks
        results = self.vectorstore.similarity_search_with_score(question, k=k)

        if not results:
            return {
                "answer": "No relevant documents found in the vector store.",
                "sources": [],
                "latency_ms": round((time.time() - start) * 1000),
                "chunks_used": 0,
                "method": "standard_rag",
            }

        # Build context from retrieved chunks
        context_parts = []
        sources = []
        for doc, score in results:
            src = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "?")
            context_parts.append(
                f"[Source: {src}, Page {page}, Relevance: {1 - score:.2f}]\n{doc.page_content}"
            )
            if src not in sources:
                sources.append(f"{src} (p.{page})")

        context = "\n\n---\n\n".join(context_parts)

        # Generate answer
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = f"""You are a knowledgeable assistant. Answer the question using ONLY the provided document excerpts.
If the documents don't contain enough information, say so clearly.
Always cite your sources (document name and page number).

Document Excerpts:
{context}

Question: {question}

Answer:"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        latency_ms = round((time.time() - start) * 1000)

        return {
            "answer": response.content,
            "sources": sources,
            "latency_ms": latency_ms,
            "chunks_used": len(results),
            "method": "standard_rag",
        }

    def is_ingested(self) -> bool:
        """Check if vector store already has documents."""
        try:
            count = self.vectorstore._collection.count()
            return count > 0
        except Exception:
            return False
