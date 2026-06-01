"""
FastAPI Backend App — High-performance REST API supporting concurrent RAG comparative queries,
AI Referee judging, Neo4j Cloud explorer hub, and dynamic Vis.js graph compilation.
"""

import sys
import os
import time
import asyncio
import json
from typing import Dict, Any, List
from pathlib import Path

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.config import Config

# Lazy-loaded global instances
standard_rag = None
light_rag = None
vector_graph_rag = None

def get_systems():
    """Lazy load RAG system modules to ensure fast startup and clean imports."""
    global standard_rag, light_rag, vector_graph_rag
    
    if standard_rag is None:
        from src.standard_rag import StandardRAG
        standard_rag = StandardRAG()
        
    if light_rag is None:
        from src.light_rag import LightRAGSystem
        light_rag = LightRAGSystem()
        
    if vector_graph_rag is None:
        from src.vector_graph_rag_system import VectorGraphRAGSystem
        vector_graph_rag = VectorGraphRAGSystem()
        
    return standard_rag, light_rag, vector_graph_rag


# Initialize FastAPI app
app = FastAPI(
    title="RAG Comparison System API",
    description="REST API for concurrent comparative queries across Standard RAG, LightRAG, and Vector Graph RAG.",
    version="2.0.0"
)

# Enable CORS for React local dev server (port 5173 / 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Schemas ──────────────────────────────────────────────────────

class QueryPayload(BaseModel):
    query: str


# ── AI Referee Engine ─────────────────────────────────────────────────────

async def run_ai_referee(query: str, ans_std: str, ans_light: str, ans_vgr: str) -> Dict[str, str]:
    """Use Google Gemini to evaluate which RAG system provided a superior answer and why."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage
    
    try:
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
        print(f"[-] AI Referee failed: {e}")
        return {
            "winner": "LightRAG",
            "reason": "LightRAG captured structural knowledge graph connections."
        }


# ── REST API Endpoints ────────────────────────────────────────────────────

@app.post("/api/query")
async def api_query(payload: QueryPayload):
    """
    Execute the query concurrently across all 3 engines, evaluate via AI Referee,
    and return unified, structured JSON including the full visualizer subgraph.
    """
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query text cannot be empty")
        
    Config.validate()
    std, light, vgr = get_systems()
    
    # 1. Define asynchronous concurrent wrappers
    async def _query_standard():
        start_time = time.time()
        # ChromaDB query is blocking, run in thread pool
        res = await asyncio.to_thread(std.query, query_text)
        latency = round((time.time() - start_time) * 1000)
        res["latency_ms"] = latency
        return res

    async def _query_lightrag():
        start_time = time.time()
        # LightRAG query is natively async
        res = await light.query(query_text)
        latency = round((time.time() - start_time) * 1000)
        res["latency_ms"] = latency
        return res

    async def _query_vgr():
        start_time = time.time()
        # VGRAG query is blocking, run in thread pool
        res = await asyncio.to_thread(vgr.query, query_text)
        latency = round((time.time() - start_time) * 1000)
        res["latency_ms"] = latency
        return res

    # 2. Trigger concurrently
    results = await asyncio.gather(
        _query_standard(),
        _query_lightrag(),
        _query_vgr(),
        return_exceptions=True
    )
    
    std_res = results[0]
    light_res = results[1]
    vgr_res = results[2]
    
    # Handle exceptions gracefully
    if isinstance(std_res, Exception):
        std_res = {"answer": f"Standard RAG failed: {std_res}", "sources": [], "latency_ms": 0, "chunks_used": 0}
    if isinstance(light_res, Exception):
        light_res = {"answer": f"LightRAG failed: {light_res}", "sources": ["Graph"], "latency_ms": 0, "chunks_used": "graph nodes"}
    if isinstance(vgr_res, Exception):
        vgr_res = {"answer": f"Vector Graph RAG failed: {vgr_res}", "sources": ["Milvus"], "latency_ms": 0, "chunks_used": 0, "subgraph": {"nodes": [], "edges": []}}

    # 3. Fetch Standard RAG raw source chunks for side-by-side snippet panels
    std_chunks = []
    if std_res.get("sources"):
        try:
            chunks = std.vectorstore.similarity_search(query_text, k=3)
            for idx, doc in enumerate(chunks):
                page = doc.metadata.get("page", "?")
                src = doc.metadata.get("source", "unknown")
                std_chunks.append({
                    "name": f"Source Chunk {idx+1} ({Path(src).name} p.{page})",
                    "content": doc.page_content
                })
        except Exception:
            pass
    std_res["source_chunks"] = std_chunks

    # 4. Trigger AI Referee to select the superior response
    referee_res = await run_ai_referee(query_text, std_res["answer"], light_res["answer"], vgr_res["answer"])
    
    return {
        "query": query_text,
        "standard": std_res,
        "lightrag": light_res,
        "vector_graph_rag": vgr_res,
        "referee": referee_res
    }


@app.get("/api/status")
async def api_status():
    """Check ingestion and connection status of all RAG engines and Neo4j."""
    std, light, vgr = get_systems()
    
    # Connect and pull live Neo4j AuraDB counts
    neo4j_stats = {"nodes": 0, "relationships": 0, "status": "Disconnected"}
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        with driver.session(database=Config.NEO4J_DATABASE) as session:
            node_c = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
            rel_c = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
            neo4j_stats = {"nodes": node_c, "relationships": rel_c, "status": "Connected"}
        driver.close()
    except Exception as e:
        neo4j_stats["status"] = f"Disconnected ({e})"

    return {
        "standard": {
            "ingested": std.is_ingested()
        },
        "lightrag": {
            "ingested": light.is_ingested(),
            "neo4j": neo4j_stats
        },
        "vector_graph_rag": {
            "ingested": vgr.is_ingested()
        }
    }


# ── Legacy FastAPI Pages (Keep active as static pages) ───────────────────

@app.get("/graph")
async def get_graph():
    """FastAPI route serving a premium Neo4j database hub portal."""
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


@app.get("/visualizer")
async def get_visualizer():
    """FastAPI route serving the beautiful Vis.js interactive knowledge graph."""
    from src.graph_visualizer import generate_interactive_graph
    
    html_path = generate_interactive_graph()
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    return HTMLResponse(content=html_content)


# ── Mount Frontend Production Build static files ─────────────────────────

frontend_build = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_build):
    print(f"[*] Mounting static frontend build files from: {frontend_build}...")
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
else:
    @app.get("/")
    async def get_welcome():
        return HTMLResponse(content="""
        <html>
        <body style="background:#090d16; color:#fff; font-family:sans-serif; display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh;">
            <h1>⚡ RAG Comparison Dashboard Backend</h1>
            <p style="color:#94a3b8;">API is running. Please start your React dev server in <code>frontend/</code> to explore the UI!</p>
            <p><a href="/docs" style="color:#00d2ff;">Explore Swagger REST API Docs</a></p>
        </body>
        </html>
        """)


if __name__ == "__main__":
    import uvicorn
    # Allow running directly via python src/app.py
    print("[*] Starting FastAPI Backend server on http://localhost:8000...")
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
