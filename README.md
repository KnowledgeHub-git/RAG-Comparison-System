# ⚡ RAG Comparison Dashboard
### Standard RAG vs. LightRAG vs. Zilliz Vector Graph RAG

Welcome to the **RAG Comparison Dashboard**—a state-of-the-art comparative ecosystem designed to benchmark and visualize three of the most advanced Retrieval-Augmented Generation (RAG) paradigms side-by-side. 

Powered by **Google Gemini** (for LLM reasoning & embeddings), **ChromaDB** (Standard Vector RAG), **LightRAG** (Synced to Neo4j AuraDB Cloud), and **Zilliz Vector Graph RAG** (local Milvus Lite), the application evaluates performance, latency, and retrieval accuracy in real-time.

---

## 🚀 Key Features

* **3-Way Side-by-Side Dashboard:** Concurrent execution of all 3 engines on every query using an asynchronous thread pool.
* **AI Referee Evaluation:** An objective Google Gemini judge evaluates the answers side-by-side, picking the Expected Winner with a structured reasoning breakdown.
* **Embedded Interactive Vis.js Graph:** Browse, search, hover, zoom, and freeze your extracted entity-relationship graph (799 nodes, 1,020 relationships) directly in the welcome screen iframe.
* **Cloud Database Explorer Hub:** Connected directly to **Neo4j AuraDB on Google Cloud** with visual stats and Bolt protocol portals.
* **Dual Runtime Interfaces:** Supports both a gorgeous, rich-aesthetics web dashboard (via Chainlit) and an optimized CLI command suite.

---

## 🏗️ The 3 RAG Architectures Compared

```
┌─────────────────────────────────────────────────────────────────────────┐
│                               USER QUERY                                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
  [ Standard RAG ]            [ LightRAG ]            [ Zilliz Vector Graph ]
  • ChromaDB Vector           • Graph + Vector        • Milvus Lite Vector
  • Raw Page Chunks           • Entity Traversal      • Triplets Indexing
  • Page-Level Similarity     • Hybrid Local+Global   • Subgraph Expansion
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │ (Concurrent Search)
                                     ▼
                        ┌─────────────────────────┐
                        │    Gemini AI Referee    │
                        └────────────┬────────────┘
                                     ▼
                        [ Expected Winner + Stats ]
```

### 1. 🗄️ Standard RAG (ChromaDB)
* **Retrieval Mode:** Classical dense vector search.
* **Granularity:** PDF text files are split into page-level chunks, vectorized, and retrieved using Cosine Similarity.
* **Best For:** Direct, single-sentence answers where details reside inside a single, local page.

### 2. 🕸️ LightRAG (Entity-Relationship Graph)
* **Retrieval Mode:** Hybrid Graph-enhanced search (local + global community traversal).
* **Granularity:** Leverages NetworkX to represent extracted document entities (locations, organizations, persons) and directed relationships with descriptions.
* **Database Backend:** Synced directly to **Neo4j AuraDB** for enterprise-grade persistent graph storage.
* **Best For:** Conceptual comparison, entity lookup, and multi-hop relationship reasoning.

### 3. ⚡ Zilliz Vector Graph RAG (Milvus Lite)
* **Retrieval Mode:** Triplet-to-passage vector index lookup inside local **Milvus Lite**.
* **Granularity:** Combines graph and vector spaces by representing entity relationships as individual passages alongside structured subject-predicate-object metadata.
* **Best For:** Fast, light graph-like vector lookups without requiring a standalone graph database.

---

## 🛠️ Robust Engineering Patches Applied

We applied targeted, leak-proof patches directly to the codebase to resolve library-level bugs:
* **Gemini JSON Boundary Parser:** A monkeypatch inside `vector_graph_rag_system.py` isolates Gemini's JSON block between `{` and `}` boundaries, neutralizing conversational chain-of-thought headers that cause standard JSON parsing crashes.
* **Top-K Reranking Safety Fallback:** Adds a fallback in VGRAG to use the top vector candidate relations if the LLM reranker filters out or fails to parse relations, preventing silent blank-context errors.
* **CLI Concurrency Upgrades:** Fully wrapped all LightRAG async coroutines inside CLI synchronous entrypoints using `asyncio.run()`, eliminating subscriptable coroutine errors in `src/main.py`.
* **Leak-Proof Ignore Policies:** Excludes local database binaries, parsed caches, HTML files, and `.env` credentials globally from Git tracking, making your project 100% secure for GitHub commits.

---

## 📦 Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.11+ installed. Clone this repository, activate your virtual environment, and install dependencies:
```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your credentials securely:
```bash
copy .env.example .env
```
Add your **Google Gemini API Key** and your **Neo4j AuraDB Cloud connection credentials**:
```ini
GEMINI_API_KEY=your_gemini_key_here
NEO4J_URI=bolt://your-auradb-uri:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_auradb_password_here
```

### 3. Ingestion (One-time Setup)
Ingest your PDFs (saved under the parent folder) into ChromaDB, LightRAG, and Zilliz Vector Graph RAG:
```bash
python src/main.py ingest
```

---

## 🚀 How to Run the System

### 1. Web Dashboard Interface (Highly Recommended)
Launch the 3-column side-by-side RAG dashboard with embedded interactive Vis.js graphs:
```bash
.venv\Scripts\chainlit run src/app.py --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your web browser:
* Explore the live interactive **Vis.js Graph visualizer** directly inside your welcome screen.
* Query comparisons and watch the **AI Referee** judge the answers side-by-side.
* Access the dedicated visualizer full-screen tab at `/visualizer` or the Neo4j Hub portal at `/graph`.

### 2. CLI Single-Query Mode
Compare responses directly in your console terminal:
```powershell
$env:PYTHONIOENCODING="utf-8"
python src/main.py query "Compare the national AI investment pledges made by Canada, France, and India."
```

### 3. CLI Interactive Chat Mode
Have a continuous chat session directly in the terminal shell:
```powershell
$env:PYTHONIOENCODING="utf-8"
python src/main.py interactive
```
