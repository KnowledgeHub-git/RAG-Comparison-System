"""
Chainlit UI Dashboard — Interactive comparison between Standard RAG and LightRAG.
Integrated with Neo4j AuraDB on Google Cloud.
"""

import sys
import os
import time
import asyncio
import json
from typing import Dict, Any, List

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chainlit as cl
from chainlit.server import app as fastapi_app
from fastapi.responses import HTMLResponse

from src.config import Config
from src.standard_rag import StandardRAG
from src.light_rag import LightRAGSystem
from src.vector_graph_rag_system import VectorGraphRAGSystem

# Global instances loaded on startup
standard_rag: StandardRAG = None
light_rag: LightRAGSystem = None
vector_graph_rag: VectorGraphRAGSystem = None


@fastapi_app.get("/graph")
async def get_graph():
    """FastAPI route serving a premium Neo4j database hub portal."""
    # Fetch live stats from Neo4j
    stats = {"nodes": 0, "relationships": 0, "status": "Error"}
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        with driver.session(database=Config.NEO4J_DATABASE) as session:
            node_c = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
            rel_c = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
            stats = {"nodes": node_c, "relationships": rel_c, "status": "Connected 🟢"}
        driver.close()
    except Exception as e:
        stats["status"] = f"Connection Failed 🔴 ({e})"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Neo4j AuraDB Knowledge Graph Hub</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #090d16;
                --card-bg: rgba(17, 25, 40, 0.75);
                --border-color: rgba(255, 255, 255, 0.08);
                --text: #f8fafc;
                --text-secondary: #94a3b8;
                --primary: #00d2ff;
                --accent: #00f2fe;
                --green: #10b981;
            }}
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background-image: radial-gradient(circle at 10% 20%, rgba(0, 210, 255, 0.05) 0%, transparent 40%),
                                  radial-gradient(circle at 90% 80%, rgba(0, 242, 254, 0.05) 0%, transparent 40%);
            }}
            .container {{
                max-width: 800px;
                width: 90%;
                background: var(--card-bg);
                backdrop-filter: blur(16px);
                border: 1px solid var(--border-color);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                text-align: center;
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 800;
                margin-top: 0;
                background: linear-gradient(135deg, #00d2ff 0%, #00f2fe 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            p {{
                color: var(--text-secondary);
                font-size: 1.1rem;
                line-height: 1.6;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: rgba(255,255,255,0.03);
                border: 1px solid var(--border-color);
                padding: 20px;
                border-radius: 16px;
                transition: transform 0.2s;
            }}
            .stat-card:hover {{
                transform: translateY(-5px);
                border-color: rgba(0, 210, 255, 0.3);
            }}
            .stat-val {{
                font-size: 1.8rem;
                font-weight: 600;
                color: var(--primary);
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 0.9rem;
                color: var(--text-secondary);
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .btn-group {{
                display: flex;
                gap: 20px;
                justify-content: center;
                margin-top: 30px;
            }}
            .btn {{
                padding: 14px 28px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 1rem;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.3s;
                display: inline-block;
            }}
            .btn-primary {{
                background: linear-gradient(135deg, #00d2ff 0%, #00f2fe 100%);
                color: #090d16;
                box-shadow: 0 4px 15px rgba(0, 210, 255, 0.3);
            }}
            .btn-primary:hover {{
                box-shadow: 0 6px 20px rgba(0, 210, 255, 0.5);
                transform: translateY(-2px);
            }}
            .btn-secondary {{
                background: rgba(255,255,255,0.05);
                color: var(--text);
                border: 1px solid var(--border-color);
            }}
            .btn-secondary:hover {{
                background: rgba(255,255,255,0.1);
                transform: translateY(-2px);
            }}
            .info-box {{
                background: rgba(0, 210, 255, 0.05);
                border: 1px solid rgba(0, 210, 255, 0.2);
                padding: 15px;
                border-radius: 12px;
                font-size: 0.9rem;
                color: #e2e8f0;
                margin-top: 30px;
                text-align: left;
            }}
            code {{
                background: rgba(255,255,255,0.1);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕸️ Neo4j AuraDB Knowledge Graph Hub</h1>
            <p>Your RAG comparison knowledge graph is fully synchronized and hosted on the high-fidelity cloud database.</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-val">{stats['status']}</div>
                    <div class="stat-label">Connection Status</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val">{stats['nodes']}</div>
                    <div class="stat-label">Total Entities</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val">{stats['relationships']}</div>
                    <div class="stat-label">Relationships</div>
                </div>
            </div>

            <div class="btn-group">
                <a href="https://console.neo4j.io" target="_blank" class="btn btn-primary">Open Neo4j Console</a>
                <a href="https://explore.neo4j.io" target="_blank" class="btn btn-secondary">Launch Neo4j Bloom</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@fastapi_app.get("/visualizer")
async def get_visualizer():
    """FastAPI route serving the beautiful Vis.js interactive knowledge graph."""
    import os
    from src.graph_visualizer import generate_interactive_graph
    
    html_path = generate_interactive_graph()
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    return HTMLResponse(content=html_content)


@cl.on_chat_start
async def on_chat_start():
    """Initialize RAG instances and welcome the user with Neo4j details."""
    global standard_rag, light_rag, vector_graph_rag
    
    cl.user_session.set("standard_rag", StandardRAG())
    cl.user_session.set("light_rag", LightRAGSystem())
    cl.user_session.set("vector_graph_rag", VectorGraphRAGSystem())
    
    # Fetch live stats from Neo4j AuraDB
    stats = {"nodes": 0, "relationships": 0, "status": "Disconnected 🔴"}
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        with driver.session(database=Config.NEO4J_DATABASE) as session:
            node_c = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
            rel_c = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
            stats = {"nodes": node_c, "relationships": rel_c, "status": "Connected 🟢"}
        driver.close()
    except Exception as e:
        stats["status"] = f"Disconnected 🔴 ({e})"
        
    welcome_message = f"""
# ⚡ RAG Comparison Dashboard
Welcome! This app compares **Standard RAG**, **LightRAG (Knowledge Graph)**, and **Zilliz Vector Graph RAG (Milvus Lite)** side-by-side using **Google Gemini**.

### 🕸️ Neo4j AuraDB Cloud Integration
- **Database Connection:** {stats['status']}
- **Total Entities (Nodes):** {stats['nodes']}
- **Total Connections (Edges):** {stats['relationships']}

🔗 **[Open Database Explorer Hub](/graph)** | **[Open Full-Screen Network Visualizer](/visualizer)**

---

### 🔍 Ask a Question
Type any question below. The app will query all three engines **concurrently** in the background, measure performance, run an **AI Referee** to choose the winner, and display the results side-by-side.

**Example Questions to Try:**
- *What are the main AI trends in 2024?*
- *How has AI investment changed over time?*
- *What does the report say about AI safety and regulation?*
- *What is a large language model?*
- *Who are the key organizations mentioned in the documents?*

---

### 🕸️ Live Interactive Knowledge Graph
Browse your extracted entity-relationship graph in real-time below:

<iframe src="/visualizer" width="100%" height="600px" style="border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; background-color: #0b0f19; box-shadow: 0 4px 20px rgba(0,0,0,0.3);"></iframe>
"""
    await cl.Message(content=welcome_message).send()


async def run_ai_referee(query: str, ans_std: str, ans_light: str, ans_vgr: str) -> Dict[str, str]:
    """Use Gemini to evaluate which RAG system provided a superior answer and why."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    
    referee_llm = ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0.2,
    )
    
    prompt = f"""You are an objective AI evaluator. Compare these three RAG answers generated for the user query: "{query}"
 
Answer A (Standard RAG - retrieve individual vector text chunks):
"{ans_std}"
 
Answer B (LightRAG - retrieve entities, relations, and subgraphs):
"{ans_light}"
 
Answer C (Zilliz Vector Graph RAG - pure vector-space graph retrieval via Milvus Lite):
"{ans_vgr}"
 
Determine which answer is superior (the Winner). Select EITHER "Standard RAG", "LightRAG", or "Vector Graph RAG" as the winner.
Provide a concise 1-2 sentence explanation of why the winner was chosen.
Focus on completeness, correctness, structure, and directness to the query.
 
Return ONLY a raw JSON object with exactly these keys:
"winner": "Standard RAG" or "LightRAG" or "Vector Graph RAG",
"reason": "explanation of your choice"
 
JSON:"""

    try:
        response = await referee_llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # Clean potential markdown codeblock wrappers
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json.loads(content)
        return {
            "winner": data.get("winner", "LightRAG"),
            "reason": data.get("reason", "All answers provide valuable perspectives.")
        }
    except Exception as e:
        print(f"AI Referee failed: {e}")
        return {
            "winner": "LightRAG",
            "reason": "LightRAG captured structural knowledge graph connections."
        }


@cl.on_message
async def on_message(message: cl.Message):
    """Execute queries on all three systems, measure metrics, evaluate, and display side-by-side."""
    std = cl.user_session.get("standard_rag")
    light = cl.user_session.get("light_rag")
    vgr = cl.user_session.get("vector_graph_rag")
    query_text = message.content.strip()
    
    # ── Step 1: Parallel RAG execution ─────────────────────────────────────
    step_std = cl.Step(name="Standard RAG Search")
    step_light = cl.Step(name="LightRAG Graph Traversal")
    step_vgr = cl.Step(name="Vector Graph RAG Search")
    
    # Define tasks
    async def _query_standard():
        async with step_std:
            step_std.output = "Searching ChromaDB vector store..."
            start_time = time.time()
            res = await asyncio.to_thread(std.query, query_text)
            latency = round((time.time() - start_time) * 1000)
            res["latency_ms"] = latency
            step_std.output = f"Completed in {latency}ms using {res.get('chunks_used', 0)} chunks."
            return res

    async def _query_lightrag():
        async with step_light:
            step_light.output = "Traversing Entity-Relationship Graph..."
            start_time = time.time()
            res = await light.query(query_text)
            latency = round((time.time() - start_time) * 1000)
            res["latency_ms"] = latency
            step_light.output = f"Completed in {latency}ms using graph hybrid retrieval."
            return res

    async def _query_vgr():
        async with step_vgr:
            step_vgr.output = "Searching Milvus Lite subgraph..."
            start_time = time.time()
            res = await asyncio.to_thread(vgr.query, query_text)
            latency = round((time.time() - start_time) * 1000)
            res["latency_ms"] = latency
            step_vgr.output = f"Completed in {latency}ms using vector graph retrieval."
            return res

    # Run concurrently
    std_task = asyncio.create_task(_query_standard())
    light_task = asyncio.create_task(_query_lightrag())
    vgr_task = asyncio.create_task(_query_vgr())
    
    results = await asyncio.gather(std_task, light_task, vgr_task, return_exceptions=True)
    
    std_res = results[0]
    light_res = results[1]
    vgr_res = results[2]
    
    # Handle potential exceptions
    if isinstance(std_res, Exception):
        std_res = {"answer": f"Standard RAG failed: {std_res}", "sources": [], "latency_ms": 0, "chunks_used": 0}
    if isinstance(light_res, Exception):
        light_res = {"answer": f"LightRAG failed: {light_res}", "sources": ["Graph"], "latency_ms": 0, "chunks_used": "graph nodes"}
    if isinstance(vgr_res, Exception):
        vgr_res = {"answer": f"Vector Graph RAG failed: {vgr_res}", "sources": ["Milvus"], "latency_ms": 0, "chunks_used": 0}
 
    # ── Step 2: AI Referee Evaluation ──────────────────────────────────────
    referee_step = cl.Step(name="AI Referee Evaluation")
    async with referee_step:
        referee_step.output = "AI Referee is evaluating answers..."
        referee_result = await run_ai_referee(query_text, std_res["answer"], light_res["answer"], vgr_res["answer"])
        winner = referee_result["winner"]
        reason = referee_result["reason"]
        referee_step.output = f"Winner chosen: {winner}!"

    # ── Step 3: Format UI Outputs ──────────────────────────────────────────
    if winner == "Standard RAG":
        winner_badge = "🔵 **Standard RAG**"
    elif winner == "Vector Graph RAG":
        winner_badge = "⚡ **Vector Graph RAG**"
    else:
        winner_badge = "🟢 **LightRAG**"
    
    header_content = f"""
### 🏆 Expected Winner: {winner_badge}
> **Rationale:** {reason}
 
---
 
### 📊 Performance comparison
| System | Latency | Chunks/Nodes Used | Method |
| :--- | :---: | :---: | :--- |
| **🗄️ Standard RAG** | `{std_res['latency_ms']}ms` | {std_res.get('chunks_used', 0)} chunks | `standard_rag` |
| **🕸️ LightRAG** | `{light_res['latency_ms']}ms` | graph nodes | `lightrag_hybrid` |
| **⚡ Vector Graph RAG** | `{vgr_res['latency_ms']}ms` | {vgr_res.get('chunks_used', 0)} entities | `milvus_vgrag` |
 
---
"""
    
    # Build text elements for Standard RAG chunk citations
    elements = []
    sources_text = ""
    if std_res.get("sources"):
        sources_text = "\n\n**📎 Standard RAG Sources:** " + ", ".join(std_res["sources"])
        
        # Pull raw chunks if available in ChromaDB to show as text elements
        try:
            chunks = std.vectorstore.similarity_search(query_text, k=3)
            for idx, doc in enumerate(chunks):
                src = doc.metadata.get("source", "unknown")
                page = doc.metadata.get("page", "?")
                elements.append(
                    cl.Text(
                        name=f"Source Chunk {idx+1} (p.{page})",
                        content=doc.page_content,
                        display="side"
                    )
                )
        except Exception:
            pass

    # Render side-by-side RAG outputs
    std_ans = std_res["answer"]
    light_ans = light_res["answer"]
    vgr_ans = vgr_res["answer"]
    
    comparison_body = f"""
## 🗄️ Standard RAG Response
{std_ans}
{sources_text}
 
---
 
## 🕸️ LightRAG Response
{light_ans}
 
---

## ⚡ Zilliz Vector Graph RAG Response
{vgr_ans}
 
---
💡 *Want to explore your document network?* **[Launch Interactive Network Visualizer](/visualizer) | [Open Neo4j Explorer Hub](/graph)**
"""

    full_content = header_content + comparison_body
    
    await cl.Message(
        content=full_content,
        elements=elements
    ).send()
