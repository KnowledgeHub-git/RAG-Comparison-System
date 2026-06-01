"""
Main CLI entry point for the RAG Comparison System.
Supports Standard RAG, LightRAG, and Zilliz Vector Graph RAG.
"""

import sys
import os

# Ensure project root is on PYTHONPATH when running as `python src/main.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.config import Config
from src.comparator import (
    compare,
    print_header,
    print_system_overview,
    print_ingestion_summary,
    console,
)

app = typer.Typer(
    name="rag-compare",
    help="RAG Comparison System — Standard RAG vs LightRAG vs Zilliz Vector Graph RAG",
    add_completion=False,
)


def _load_systems():
    """Lazy-load all 3 RAG systems."""
    from src.standard_rag import StandardRAG
    from src.light_rag import LightRAGSystem
    from src.vector_graph_rag_system import VectorGraphRAGSystem

    standard = StandardRAG()
    lightrag = LightRAGSystem()
    vector_graph_rag = VectorGraphRAGSystem()
    return standard, lightrag, vector_graph_rag


@app.command()
def ingest(
    pdf_dir: Optional[str] = typer.Option(
        None,
        "--pdf-dir",
        help="Override PDF directory path",
    ),
):
    """
    Ingest your PDFs into all 3 RAG systems (Standard, LightRAG, and Zilliz Vector Graph RAG).
    This only needs to be run once. Results are persisted locally to disk.
    """
    print_header()
    Config.validate()

    pdf_directory = pdf_dir or str(Config.PDF_DIR)
    console.print(f"[bold]📂 PDF Directory:[/bold] {pdf_directory}")
    console.print()

    # Load PDFs
    console.print("[bold cyan]Step 1/4:[/bold cyan] Loading PDFs...")
    from src.pdf_loader import load_pdfs
    try:
        documents = load_pdfs(pdf_directory)
    except FileNotFoundError as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)

    results = {}

    # ── Standard RAG ──────────────────────────────────────────────────────
    console.print("\n[bold cyan]Step 2/4:[/bold cyan] Ingesting into Standard RAG (ChromaDB)...")
    from src.standard_rag import StandardRAG
    standard = StandardRAG()

    if standard.is_ingested():
        console.print("  [yellow]⏭️  Standard RAG already has data — skipping (delete chroma_db/ to re-ingest)[/yellow]")
        results["standard"] = -1
    else:
        count = standard.ingest(documents)
        results["standard"] = count

    # ── LightRAG ──────────────────────────────────────────────────────────
    console.print("\n[bold cyan]Step 3/4:[/bold cyan] Ingesting into LightRAG (Knowledge Graph)...")
    from src.light_rag import LightRAGSystem
    lightrag = LightRAGSystem()

    if lightrag.is_ingested():
        console.print("  [yellow]⏭️  LightRAG already has data — skipping (delete output/lightrag/ to re-ingest)[/yellow]")
        results["lightrag"] = -1
    else:
        count = lightrag.ingest(documents)
        results["lightrag"] = count

    # ── Zilliz Vector Graph RAG ───────────────────────────────────────────
    console.print("\n[bold cyan]Step 4/4:[/bold cyan] Ingesting into Zilliz Vector Graph RAG (Milvus Lite)...")
    from src.vector_graph_rag_system import VectorGraphRAGSystem
    vgr = VectorGraphRAGSystem()

    if vgr.is_ingested():
        console.print("  [yellow]⏭️  Zilliz Vector Graph RAG already has data — skipping (delete output/vector_graph_rag/ to re-ingest)[/yellow]")
        results["vector_graph_rag"] = -1
    else:
        count = vgr.ingest(documents)
        results["vector_graph_rag"] = count

    print_ingestion_summary(
        {k: v for k, v in results.items() if v != -1}
    )
    console.print("[bold green]✅ Ingestion complete! Run `python src/main.py query \"your question\"` to compare.[/bold green]")


@app.command()
def query(
    question: str = typer.Argument(..., help="The question to ask all 3 RAG systems"),
):
    """
    Ask a question and compare answers from all 3 RAG systems side-by-side.
    """
    print_header()
    Config.validate()

    standard_result = None
    lightrag_result = None
    vgr_result = None

    # ── Standard RAG ──────────────────────────────────────────────────────
    console.print("[cyan]🗄️  Querying Standard RAG...[/cyan]")
    from src.standard_rag import StandardRAG
    standard = StandardRAG()
    if not standard.is_ingested():
        console.print("  [yellow]⚠️  Standard RAG not ingested. Run: python src/main.py ingest[/yellow]")
    else:
        standard_result = standard.query(question)
        console.print(f"  ✅ Done ({standard_result['latency_ms']}ms)")

    # ── LightRAG ──────────────────────────────────────────────────────────
    console.print("[green]🕸️  Querying LightRAG...[/green]")
    from src.light_rag import LightRAGSystem
    lightrag = LightRAGSystem()
    if not lightrag.is_ingested():
        console.print("  [yellow]⚠️  LightRAG not ingested. Run: python src/main.py ingest[/yellow]")
    else:
        import asyncio
        lightrag_result = asyncio.run(lightrag.query(question))
        console.print(f"  ✅ Done ({lightrag_result['latency_ms']}ms)")

    # ── Zilliz Vector Graph RAG ───────────────────────────────────────────
    console.print("[magenta]⚡  Querying Zilliz Vector Graph RAG...[/magenta]")
    from src.vector_graph_rag_system import VectorGraphRAGSystem
    vgr = VectorGraphRAGSystem()
    if not vgr.is_ingested():
        console.print("  [yellow]⚠️  Zilliz Vector Graph RAG not ingested. Run: python src/main.py ingest[/yellow]")
    else:
        vgr_result = vgr.query(question)
        console.print(f"  ✅ Done ({vgr_result['latency_ms']}ms)")

    # ── Display comparison ─────────────────────────────────────────────────
    # We pass vgr_result under the graphrag_result slot inside the rich visual comparator to reuse existing structures
    compare(
        question=question,
        standard_result=standard_result,
        lightrag_result=lightrag_result,
        graphrag_result=vgr_result,
        skip_graphrag=False,
    )


@app.command()
def interactive():
    """
    Start an interactive comparison session.
    Ask questions one at a time and see all 3 systems respond.
    """
    print_header()
    print_system_overview()
    Config.validate()

    EXAMPLE_QUERIES = [
        "What are the main AI trends in 2025?",
        "Who are the key organizations mentioned in the documents?",
        "What does the report say about AI safety and regulation?",
        "How has AI investment changed over time?",
        "What is a large language model?",
    ]

    console.print("[bold]💡 Example questions to try:[/bold]")
    for i, q in enumerate(EXAMPLE_QUERIES, 1):
        console.print(f"  {i}. {q}")
    console.print()
    console.print("[dim]Type 'quit' to exit, 'examples' to see example questions[/dim]")
    console.print()

    from src.standard_rag import StandardRAG
    from src.light_rag import LightRAGSystem
    from src.vector_graph_rag_system import VectorGraphRAGSystem
    
    standard = StandardRAG()
    lightrag = LightRAGSystem()
    vgr = VectorGraphRAGSystem()

    while True:
        try:
            question = Prompt.ask("\n[bold yellow]❓ Your question[/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break
        if question.lower() == "examples":
            for i, q in enumerate(EXAMPLE_QUERIES, 1):
                console.print(f"  {i}. {q}")
            continue

        # Run queries
        standard_result = standard.query(question) if standard.is_ingested() else None
        import asyncio
        lightrag_result = asyncio.run(lightrag.query(question)) if lightrag.is_ingested() else None
        vgr_result = vgr.query(question) if vgr.is_ingested() else None

        compare(
            question=question,
            standard_result=standard_result,
            lightrag_result=lightrag_result,
            graphrag_result=vgr_result,
            skip_graphrag=False,
        )


@app.command()
def status():
    """Check the ingestion status of all 3 RAG systems."""
    print_header()
    Config.validate()

    from src.standard_rag import StandardRAG
    from src.light_rag import LightRAGSystem
    from src.vector_graph_rag_system import VectorGraphRAGSystem

    systems = [
        ("Standard RAG", StandardRAG(), "cyan"),
        ("LightRAG", LightRAGSystem(), "green"),
        ("Vector Graph RAG", VectorGraphRAGSystem(), "magenta"),
    ]

    console.print("[bold]📊 Ingestion Status[/bold]\n")
    for name, system, color in systems:
        ingested = system.is_ingested()
        icon = "✅" if ingested else "❌"
        status_text = "Ready" if ingested else "Not ingested — run: python src/main.py ingest"
        console.print(f"  [{color}]{icon} {name}[/{color}]: {status_text}")

    console.print(f"\n[dim]Config: {Config.summary()}[/dim]")


if __name__ == "__main__":
    app()
