"""
LightRAG — Efficient Graph-Enhanced RAG with incremental updates.

Uses lightrag-hku with Google Gemini as both LLM and embedding provider.

Key advantage over Standard RAG:
  - Builds a knowledge GRAPH of entities and relationships
  - Supports incremental document addition (no full re-index needed)
  - Hybrid retrieval: graph traversal + vector search

Key advantage over Microsoft GraphRAG:
  - Much cheaper to index
  - Faster setup
  - Incremental updates without rebuilding everything
"""

import os
import time
import asyncio
from typing import List, Dict, Any

from src.config import Config
from src.pdf_loader import Document


class LightRAGSystem:
    """
    LightRAG wrapper using Gemini LLM + embeddings.

    Architecture:
      INSERT: text → LLM extracts entities/relations → builds KG + vectors
      QUERY:  question → hybrid graph+vector search → LLM synthesizes answer
    """

    def __init__(self):
        Config.validate()
        os.makedirs(Config.LIGHTRAG_DIR, exist_ok=True)
        self._rag = None

    def _build_rag(self):
        """Lazily initialize LightRAG with Gemini functions."""
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.gemini import gemini_complete_if_cache, gemini_embed
        from lightrag.utils import EmbeddingFunc
        import numpy as np

        async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            """Gemini LLM function for LightRAG."""
            return await gemini_complete_if_cache(
                model=Config.GEMINI_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=Config.GEMINI_API_KEY,
                **kwargs,
            )

        async def embedding_func(texts: list[str]) -> np.ndarray:
            """Gemini embedding function for LightRAG."""
            from google import genai
            import numpy as np
            import asyncio

            client = genai.Client(api_key=Config.GEMINI_API_KEY)
            
            async def _embed_single(text: str):
                model_name = Config.GEMINI_EMBEDDING_MODEL.replace("models/", "")
                response = await client.aio.models.embed_content(
                    model=model_name,
                    contents=text,
                )
                return response.embeddings[0].values

            # Call embedding API in parallel for all texts in batch
            tasks = [_embed_single(t) for t in texts]
            results = await asyncio.gather(*tasks)
            return np.array(results, dtype=np.float32)

        self._rag = LightRAG(
            working_dir=Config.LIGHTRAG_DIR,
            llm_model_func=llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=3072,  # gemini-embedding-2 dimension
                max_token_size=2048,
                func=embedding_func,
            ),
        )
        return self._rag

    @property
    def rag(self):
        if self._rag is None:
            self._build_rag()
        return self._rag

    def ingest(self, documents: List[Document]) -> int:
        """
        Incrementally insert documents into LightRAG.

        Unlike GraphRAG, new documents can be added without rebuilding the index.
        """
        # Combine all text chunks for insertion
        texts = [doc.page_content for doc in documents]

        print(f"    LightRAG: inserting {len(texts)} chunks (building knowledge graph)...")
        print("    ⚠️  This uses the LLM to extract entities — may take a few minutes...")

        # LightRAG's insert is async
        async def _insert():
            await self.rag.initialize_storages()
            # Insert in batches of 20 to manage rate limits
            batch_size = 20
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                combined = "\n\n".join(batch)
                await self.rag.ainsert(combined)
                print(f"    LightRAG: processed {min(i + batch_size, len(texts))}/{len(texts)} chunks...")
                await asyncio.sleep(1)  # rate limit pause

        asyncio.run(_insert())
        print(f"    ✅ LightRAG: {len(texts)} chunks ingested into knowledge graph")
        return len(texts)

    async def query(self, question: str, mode: str = "hybrid") -> Dict[str, Any]:
        """
        Query LightRAG using hybrid graph + vector retrieval.

        Modes:
          - 'naive':  pure vector similarity (similar to Standard RAG)
          - 'local':  entity-centric graph search
          - 'global': community-level global search
          - 'hybrid': combines local + global (recommended)
        """
        from lightrag import QueryParam
        import time

        start = time.time()

        await self.rag.initialize_storages()
        try:
            answer = await self.rag.aquery(
                question,
                param=QueryParam(mode=mode),
            )
        except Exception as e:
            print(f"LightRAG Query Error: {e}")
            answer = f"Error: {e}"

        latency_ms = round((time.time() - start) * 1000)

        return {
            "answer": answer if answer else "No answer generated.",
            "sources": ["Knowledge Graph (entities + relationships)"],
            "latency_ms": latency_ms,
            "chunks_used": "graph nodes",
            "method": f"lightrag_{mode}",
        }

    def is_ingested(self) -> bool:
        """Check if LightRAG working directory has data."""
        working_dir = Config.LIGHTRAG_DIR
        required_files = ["graph_chunk_entity_relation.graphml", "kv_store_full_docs.json"]
        return any(
            os.path.exists(os.path.join(working_dir, f))
            for f in required_files
        )
