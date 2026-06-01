"""
Microsoft GraphRAG — Knowledge Graph-based RAG with community summaries.

Uses the official 'graphrag' library configured with Google Gemini via LiteLLM.

Key advantage over Standard RAG:
  - Builds a full knowledge graph with entity communities
  - Pre-generates community summaries → answers global/thematic questions
  - Can answer: "What are the main themes?" across ALL documents at once

Trade-off:
  - Expensive upfront indexing (LLM reads every chunk for entity extraction)
  - Slower to set up but powerful for large-scale document analysis
"""

import os
import time
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

from src.config import Config
from src.pdf_loader import Document

# GraphRAG settings template using Gemini via LiteLLM
GRAPHRAG_SETTINGS_TEMPLATE = """
# GraphRAG Settings — Gemini via LiteLLM
# Auto-generated — do not edit manually

models:
  default_chat_model:
    type: openai_chat
    api_base: https://generativelanguage.googleapis.com/v1beta/openai
    api_key: {api_key}
    model: gemini-2.5-flash
    max_tokens: 4000
    temperature: 0
    
  default_embedding_model:
    type: openai_embedding
    api_base: https://generativelanguage.googleapis.com/v1beta/openai
    api_key: {api_key}
    model: gemini-embedding-2

input:
  type: file
  file_type: text
  base_dir: "input"

storage:
  type: file
  base_dir: "output"

cache:
  type: file
  base_dir: "cache"

reporting:
  type: file
  base_dir: "logs"

chunks:
  size: 1000
  overlap: 100
  group_by_columns: [id]

embeddings:
  target: required
  
entity_extraction:
  max_gleanings: 1

community_reports:
  max_length: 2000
  max_input_length: 8000

claim_extraction:
  enabled: false

local_search:
  text_unit_prop: 0.5
  community_prop: 0.1
  conversation_history_max_turns: 5
  top_k_mapped_entities: 10
  top_k_relationships: 10
  max_tokens: 4000

global_search:
  max_tokens: 4000
  data_max_tokens: 3000
  map_max_tokens: 1000
  reduce_max_tokens: 2000
  concurrency: 32
"""


class GraphRAGSystem:
    """
    Microsoft GraphRAG wrapper configured with Gemini API.

    Two query modes:
      - 'global': uses community summaries → great for big-picture questions
      - 'local':  uses entity subgraphs → great for specific entity questions
    """

    def __init__(self):
        Config.validate()
        self._graphrag_dir = Path(Config.GRAPHRAG_DIR)
        self._input_dir = self._graphrag_dir / "input"
        self._settings_file = self._graphrag_dir / "settings.yaml"
        os.makedirs(self._input_dir, exist_ok=True)

    def _setup_settings(self):
        """Write Gemini-configured settings.yaml for GraphRAG."""
        settings_content = GRAPHRAG_SETTINGS_TEMPLATE.format(
            api_key=Config.GEMINI_API_KEY
        )
        self._settings_file.write_text(settings_content.strip(), encoding="utf-8")
        print(f"    GraphRAG: settings.yaml written with Gemini config")

    def _write_documents_to_input(self, documents: List[Document]) -> int:
        """Write document chunks as text files for GraphRAG to process."""
        # Group chunks by source PDF
        by_source: Dict[str, List[str]] = {}
        for doc in documents:
            src = doc.metadata.get("source", "unknown")
            by_source.setdefault(src, []).append(doc.page_content)

        count = 0
        for source, chunks in by_source.items():
            # Write each PDF as a single combined .txt file
            safe_name = source.replace(".pdf", "").replace(" ", "_")
            out_file = self._input_dir / f"{safe_name}.txt"
            out_file.write_text("\n\n".join(chunks), encoding="utf-8")
            count += len(chunks)
            print(f"    GraphRAG: wrote {safe_name}.txt ({len(chunks)} chunks)")

        return count

    def ingest(self, documents: List[Document]) -> int:
        """
        Run GraphRAG indexing pipeline.

        WARNING: This calls the LLM for every chunk to extract entities.
        Cost is proportional to document size. Use gpt-4o-mini or gemini-flash.
        """
        print("    GraphRAG: setting up configuration...")
        self._setup_settings()

        print("    GraphRAG: writing documents to input directory...")
        count = self._write_documents_to_input(documents)

        print("\n    ⚠️  GraphRAG: starting indexing pipeline...")
        print("    ⚠️  This will make many LLM calls — may take 5-30 minutes depending on doc size")
        print("    ⚠️  Cost estimate: $0.50-3.00 for your PDFs with gemini-2.5-flash\n")

        cmd = [
            str(Path(Config.GRAPHRAG_DIR).parent.parent / ".venv" / "Scripts" / "graphrag"),
            "index",
            "--root", str(self._graphrag_dir),
        ]

        # Fallback to python -m graphrag
        python_path = str(
            Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
        )

        try:
            result = subprocess.run(
                [python_path, "-m", "graphrag", "index", "--root", str(self._graphrag_dir)],
                capture_output=False,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
            if result.returncode == 0:
                print("\n    ✅ GraphRAG: indexing complete!")
            else:
                print(f"\n    ❌ GraphRAG indexing failed (exit code {result.returncode})")
        except subprocess.TimeoutExpired:
            print("\n    ❌ GraphRAG indexing timed out after 1 hour")
        except Exception as e:
            print(f"\n    ❌ GraphRAG indexing error: {e}")

        return count

    def query(self, question: str, method: str = "global") -> Dict[str, Any]:
        """
        Query GraphRAG using global or local search.

        Args:
            question: The question to answer
            method: 'global' (thematic/big-picture) or 'local' (entity-specific)
        """
        start = time.time()

        if not self.is_ingested():
            return {
                "answer": (
                    "⚠️  GraphRAG has not been indexed yet.\n"
                    "Run: python src/main.py ingest --systems graphrag\n"
                    "Note: Indexing is expensive (~$0.50-3.00). Use --skip-graphrag to skip."
                ),
                "sources": [],
                "latency_ms": 0,
                "chunks_used": 0,
                "method": f"graphrag_{method}",
            }

        python_path = str(
            Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
        )

        try:
            result = subprocess.run(
                [
                    python_path, "-m", "graphrag", "query",
                    "--root", str(self._graphrag_dir),
                    "--method", method,
                    "--query", question,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            answer = result.stdout.strip() if result.stdout else result.stderr.strip()
            if not answer:
                answer = "GraphRAG returned no response."
        except subprocess.TimeoutExpired:
            answer = "GraphRAG query timed out."
        except Exception as e:
            answer = f"GraphRAG query error: {e}"

        latency_ms = round((time.time() - start) * 1000)

        return {
            "answer": answer,
            "sources": [f"Community summaries ({method} search)"],
            "latency_ms": latency_ms,
            "chunks_used": "graph communities",
            "method": f"graphrag_{method}",
        }

    def is_ingested(self) -> bool:
        """Check if GraphRAG output directory has parquet files (index complete)."""
        output_dir = self._graphrag_dir / "output"
        if not output_dir.exists():
            return False
        parquet_files = list(output_dir.rglob("*.parquet"))
        return len(parquet_files) > 0
