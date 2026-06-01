"""
Comparator — runs all 3 RAG systems on the same query and displays results side-by-side.

Uses the Rich library for beautiful terminal output.
"""

import time
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule

console = Console()


SYSTEM_DESCRIPTIONS = {
    "standard": {
        "name": "Standard RAG",
        "icon": "🗄️ ",
        "color": "cyan",
        "metaphor": "Filing Cabinet",
        "description": "Chunk → Embed → Cosine Search → LLM Answer",
    },
    "lightrag": {
        "name": "LightRAG",
        "icon": "🕸️ ",
        "color": "green",
        "metaphor": "Smart Graph Cabinet",
        "description": "Graph + Vector Hybrid (incremental, efficient)",
    },
    "graphrag": {
        "name": "Microsoft GraphRAG",
        "icon": "🔍",
        "color": "magenta",
        "metaphor": "Detective's Case Board",
        "description": "Entity Graph + Community Summaries (global synthesis)",
    },
}


def print_header():
    """Print a welcome banner."""
    console.print()
    console.rule("[bold blue]⚡ RAG Comparison System[/bold blue]")
    console.print(
        "[dim]Comparing: Standard RAG vs LightRAG vs Microsoft GraphRAG[/dim]",
        justify="center",
    )
    console.print()


def print_system_overview():
    """Print a brief explanation of each system."""
    table = Table(
        title="RAG Systems Overview",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )
    table.add_column("System", style="bold", min_width=20)
    table.add_column("Metaphor", min_width=20)
    table.add_column("How It Works", min_width=40)
    table.add_column("Best For", min_width=30)

    table.add_row(
        "[cyan]🗄️  Standard RAG[/cyan]",
        "Filing Cabinet",
        "Chunks → Vectors → Similarity Search",
        "Specific factual questions",
    )
    table.add_row(
        "[green]🕸️  LightRAG[/green]",
        "Smart Graph Cabinet",
        "Graph + Vector Hybrid Retrieval",
        "Entity relationships, balanced queries",
    )
    table.add_row(
        "[magenta]🔍 Microsoft GraphRAG[/magenta]",
        "Detective's Case Board",
        "Community Summaries from full KG",
        "Global themes, cross-document synthesis",
    )

    console.print(table)
    console.print()


def compare(
    question: str,
    standard_result: Optional[Dict[str, Any]] = None,
    lightrag_result: Optional[Dict[str, Any]] = None,
    graphrag_result: Optional[Dict[str, Any]] = None,
    skip_graphrag: bool = False,
) -> None:
    """
    Display a side-by-side comparison of all 3 RAG system results.
    """
    console.print()
    console.rule(f"[bold yellow]Query[/bold yellow]")
    console.print(Panel(f"[bold white]{question}[/bold white]", border_style="yellow"))
    console.print()

    results = []
    if standard_result:
        results.append(("standard", standard_result))
    if lightrag_result:
        results.append(("lightrag", lightrag_result))
    if graphrag_result or skip_graphrag:
        results.append(("graphrag", graphrag_result or {}))

    # ── Metrics Summary Table ────────────────────────────────────────────────
    summary_table = Table(
        title="📊 Performance Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white",
    )
    summary_table.add_column("System", style="bold", min_width=22)
    summary_table.add_column("Latency", justify="right", min_width=10)
    summary_table.add_column("Sources/Nodes", justify="center", min_width=15)
    summary_table.add_column("Method", min_width=20)

    for system_key, result in results:
        info = SYSTEM_DESCRIPTIONS[system_key]
        if not result:
            summary_table.add_row(
                f"[{info['color']}]{info['icon']} {info['name']}[/{info['color']}]",
                "[dim]skipped[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
            )
        else:
            latency = result.get("latency_ms", 0)
            latency_str = f"{latency}ms" if latency < 2000 else f"{latency/1000:.1f}s"
            sources = result.get("chunks_used", "?")
            method = result.get("method", "?")
            summary_table.add_row(
                f"[{info['color']}]{info['icon']} {info['name']}[/{info['color']}]",
                f"[{'green' if latency < 3000 else 'yellow'}]{latency_str}[/{'green' if latency < 3000 else 'yellow'}]",
                str(sources),
                f"[dim]{method}[/dim]",
            )

    console.print(summary_table)
    console.print()

    # ── Individual Answer Panels ─────────────────────────────────────────────
    for system_key, result in results:
        info = SYSTEM_DESCRIPTIONS[system_key]
        color = info["color"]

        if not result:
            console.print(
                Panel(
                    "[dim]Skipped (use --include-graphrag to enable)[/dim]",
                    title=f"[{color}]{info['icon']} {info['name']} — SKIPPED[/{color}]",
                    border_style=color,
                )
            )
        else:
            answer = result.get("answer", "No answer.")
            sources = result.get("sources", [])

            sources_text = ""
            if sources:
                sources_text = f"\n\n[dim]📎 Sources: {', '.join(str(s) for s in sources[:3])}[/dim]"

            content = Text()
            content.append(answer[:1500])  # truncate very long answers
            if len(answer) > 1500:
                content.append("\n[...answer truncated for display...]", style="dim")

            console.print(
                Panel(
                    str(content) + sources_text,
                    title=f"[{color} bold]{info['icon']} {info['name']}[/{color} bold]  [dim]{info['metaphor']}[/dim]",
                    border_style=color,
                    padding=(1, 2),
                )
            )

    console.print()
    console.rule("[dim]End of comparison[/dim]")
    console.print()


def print_ingestion_summary(results: Dict[str, int]):
    """Print ingestion results table."""
    table = Table(
        title="📥 Ingestion Summary",
        box=box.ROUNDED,
        header_style="bold",
    )
    table.add_column("System", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Items Processed", justify="right")

    for system, count in results.items():
        info = SYSTEM_DESCRIPTIONS.get(system, {"name": system, "color": "white", "icon": ""})
        status = "✅ Done" if count > 0 else "⏭️  Skipped"
        table.add_row(
            f"[{info['color']}]{info['icon']} {info['name']}[/{info['color']}]",
            status,
            str(count) if count > 0 else "—",
        )

    console.print(table)
    console.print()
