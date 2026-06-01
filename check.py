"""
Health check — verifies the full project setup is working correctly.
Results are written to check_report.txt (avoids console encoding issues).
"""
import sys, os, pathlib, time

# Write results to file to avoid Windows console encoding issues
REPORT_FILE = "check_report.txt"
lines = []

def log(msg=""):
    lines.append(msg)

def save():
    pathlib.Path(REPORT_FILE).write_text("\n".join(lines), encoding="utf-8")

# ── Setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log("=" * 55)
log("  RAG Comparison System - Health Check")
log(f"  Run at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 55)

# ── [1] Config ────────────────────────────────────────────────────────────
log("\n[1] Config")
try:
    from src.config import Config
    Config.validate()
    key_preview = Config.GEMINI_API_KEY[:10] + "..." if Config.GEMINI_API_KEY else "NOT SET"
    log(f"    Gemini Model     : {Config.GEMINI_MODEL}")
    log(f"    Embedding Model  : {Config.GEMINI_EMBEDDING_MODEL}")
    log(f"    API Key          : {key_preview}")
    log(f"    DeepSeek enabled : {Config.has_deepseek()}")
    log("    Status           : OK")
except Exception as e:
    log(f"    ERROR: {e}")
    save(); sys.exit(1)

# ── [2] PDF Directory ─────────────────────────────────────────────────────
log("\n[2] PDF Directory")
pdf_path = pathlib.Path(Config.PDF_DIR)
resolved = pdf_path.resolve()
log(f"    Path    : {resolved}")
log(f"    Exists  : {pdf_path.exists()}")

pdfs = list(pdf_path.glob("*.pdf")) if pdf_path.exists() else []
if not pdfs:
    log("    ERROR: No PDFs found!")
    save(); sys.exit(1)

for p in pdfs:
    size_mb = p.stat().st_size / 1024 / 1024
    log(f"    PDF     : {p.name}  ({size_mb:.1f} MB)")

# ── [3] PDF Extraction ────────────────────────────────────────────────────
log("\n[3] PDF Text Extraction (PyMuPDF)")
try:
    import fitz
    total_pages = 0
    total_chars = 0
    for p in pdfs:
        t0 = time.time()
        doc = fitz.open(str(p))
        pages = len(doc)
        chars = sum(len(page.get_text("text")) for page in doc)
        doc.close()
        elapsed = time.time() - t0
        log(f"    {p.name}: {pages} pages, {chars:,} chars in {elapsed:.1f}s")
        total_pages += pages
        total_chars += chars
    log(f"    TOTAL: {total_pages} pages, {total_chars:,} characters")
    log("    Status: OK")
except Exception as e:
    log(f"    ERROR: {e}")

# ── [4] PDF Chunking ──────────────────────────────────────────────────────
log("\n[4] PDF Chunking (full load_pdfs)")
try:
    from src.pdf_loader import load_pdfs
    t0 = time.time()
    docs = load_pdfs(str(Config.PDF_DIR))
    elapsed = time.time() - t0
    log(f"    Total chunks     : {len(docs)}")
    log(f"    Time             : {elapsed:.1f}s")
    log(f"    First chunk src  : {docs[0].metadata.get('source')}")
    log(f"    First chunk page : {docs[0].metadata.get('page')}")
    log(f"    First 100 chars  : {docs[0].page_content[:100].strip()!r}")
    log("    Status: OK")
except Exception as e:
    log(f"    ERROR: {e}")
    import traceback
    log(traceback.format_exc())

# ── [5] Package Imports ───────────────────────────────────────────────────
log("\n[5] Package Imports")
packages = {
    "chromadb": "chromadb",
    "langchain_google_genai": "langchain-google-genai",
    "lightrag": "lightrag-hku",
    "fitz": "pymupdf",
    "rich": "rich",
    "typer": "typer",
    "langgraph": "langgraph",
    "langchain_community": "langchain-community",
}
all_ok = True
for mod, pkg in packages.items():
    try:
        __import__(mod)
        log(f"    OK      {pkg}")
    except ImportError as e:
        log(f"    MISSING {pkg}  (pip install {pkg})")
        all_ok = False
log(f"    Status: {'OK' if all_ok else 'SOME PACKAGES MISSING'}")

# ── [6] Source Files ──────────────────────────────────────────────────────
log("\n[6] Source Files")
src_files = [
    "src/__init__.py", "src/config.py", "src/pdf_loader.py",
    "src/standard_rag.py", "src/light_rag.py",
    "src/graph_rag.py", "src/comparator.py", "src/main.py",
    ".env", ".gitignore", ".env.example", "requirements.txt",
]
root = pathlib.Path(".")
all_present = True
for f in src_files:
    exists = (root / f).exists()
    size = (root / f).stat().st_size if exists else 0
    log(f"    {'OK' if exists else 'MISSING':8}  {f}  ({size} bytes)")
    if not exists:
        all_present = False
log(f"    Status: {'OK' if all_present else 'SOME FILES MISSING'}")

# ── [7] Ingestion Status ──────────────────────────────────────────────────
log("\n[7] Ingestion Status (have PDFs been indexed yet?)")
chroma_ready = pathlib.Path(Config.CHROMA_DIR, "chroma.sqlite3").exists()
lightrag_ready = any(
    pathlib.Path(Config.LIGHTRAG_DIR, f).exists()
    for f in ["graph_chunk_entity_relation.graphml", "kv_store_full_docs.json"]
)
graphrag_ready = len(list(pathlib.Path(Config.GRAPHRAG_DIR).rglob("*.parquet"))) > 0 \
    if pathlib.Path(Config.GRAPHRAG_DIR).exists() else False

log(f"    Standard RAG (ChromaDB) : {'READY' if chroma_ready else 'Not ingested yet'}")
log(f"    LightRAG                : {'READY' if lightrag_ready else 'Not ingested yet'}")
log(f"    Microsoft GraphRAG      : {'READY' if graphrag_ready else 'Not ingested yet'}")

# ── Summary ───────────────────────────────────────────────────────────────
log("\n" + "=" * 55)
log("  HEALTH CHECK COMPLETE")
log("=" * 55)
log("\nNext steps:")
log("  .venv\\Scripts\\activate")
log("  python src/main.py ingest              # index PDFs (Standard + LightRAG)")
log("  python src/main.py query \"What are AI trends in 2025?\"")
log("  python src/main.py interactive         # interactive chat mode")

save()
print(f"Report saved to: {pathlib.Path(REPORT_FILE).resolve()}")
