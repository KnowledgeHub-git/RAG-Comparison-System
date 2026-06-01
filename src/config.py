"""Configuration — loads .env and exposes all settings securely."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the project root (one level up from src/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Config:
    # ── Google Gemini ──────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_EMBEDDING_MODEL: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2"
    )

    # ── DeepSeek (optional) ────────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # ── Paths ──────────────────────────────────────────────────────────────
    _root = Path(__file__).resolve().parent.parent
    PDF_DIR: Path = Path(os.getenv("PDF_DIR", str(_root.parent / "PDFs")))
    CHROMA_DIR: str = str(_root / "chroma_db")
    LIGHTRAG_DIR: str = str(_root / "output" / "lightrag")
    GRAPHRAG_DIR: str = str(_root / "output" / "graphrag")
    DATA_DIR: str = str(_root / "data" / "documents")

    # ── Neo4j Configuration ─────────────────────────────────────────────────
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    NEO4J_GRAPHQL_URL: str = os.getenv("NEO4J_GRAPHQL_URL", "")
    NEO4J_GRAPHQL_API_KEY: str = os.getenv("NEO4J_GRAPHQL_API_KEY", "")

    @classmethod
    def validate(cls) -> None:
        """Raise a clear error if required keys are missing."""
        if not cls.GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.\n"
                "  1. Copy .env.example to .env\n"
                "  2. Add your Gemini API key from https://aistudio.google.com/apikey"
            )

    @classmethod
    def has_deepseek(cls) -> bool:
        return bool(cls.DEEPSEEK_API_KEY and cls.DEEPSEEK_API_KEY != "your_deepseek_key_here")

    @classmethod
    def summary(cls) -> str:
        lines = [
            "-- Configuration --------------------------------",
            f"  Gemini Model      : {cls.GEMINI_MODEL}",
            f"  Embedding Model   : {cls.GEMINI_EMBEDDING_MODEL}",
            f"  DeepSeek enabled  : {cls.has_deepseek()}",
            f"  PDF directory     : {cls.PDF_DIR}",
            f"  ChromaDB dir      : {cls.CHROMA_DIR}",
            f"  LightRAG dir      : {cls.LIGHTRAG_DIR}",
            f"  GraphRAG dir      : {cls.GRAPHRAG_DIR}",
            f"  Neo4j URI         : {cls.NEO4J_URI}",
            f"  Neo4j Username    : {cls.NEO4J_USERNAME}",
            "-------------------------------------------------",
        ]
        return "\n".join(lines)
