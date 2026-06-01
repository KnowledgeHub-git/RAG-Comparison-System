"""PDF Loader — extracts and chunks text from PDF files using PyMuPDF."""

import os
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF


class Document:
    """Simple document container."""

    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata

    def __repr__(self) -> str:
        preview = self.page_content[:80].replace("\n", " ")
        return f"Document(source={self.metadata.get('source')}, page={self.metadata.get('page')}, preview='{preview}...')"


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text page by page from a PDF file."""
    pages = []
    doc = fitz.open(pdf_path)
    filename = Path(pdf_path).name

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:  # skip blank pages
            pages.append({
                "text": text,
                "page": page_num,
                "source": filename,
                "path": str(pdf_path),
            })

    doc.close()
    return pages


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    text_len = len(text)

    # If the text is very short, just return it as a single chunk
    if text_len <= chunk_size:
        text = text.strip()
        if len(text) > 50:
            return [text]
        return []

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a sentence boundary
        if end < text_len:
            last_period = chunk.rfind(". ")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk = chunk[: break_point + 1]

        chunk = chunk.strip()
        if len(chunk) > 50:  # skip tiny fragments
            chunks.append(chunk)

        # Ensure we always make progress to prevent infinite loops
        step = len(chunk) - chunk_overlap
        if start + len(chunk) >= text_len or step <= 0:
            break

        start += step

    return chunks


def load_pdfs(pdf_dir: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> List[Document]:
    """
    Load all PDFs from a directory, extract text, and return chunked Documents.

    Args:
        pdf_dir: Path to directory containing PDF files.
        chunk_size: Characters per chunk (default 1000).
        chunk_overlap: Overlap between chunks (default 150).

    Returns:
        List of Document objects ready for ingestion.
    """
    pdf_dir_path = Path(pdf_dir)
    if not pdf_dir_path.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {pdf_dir}")

    all_documents: List[Document] = []

    for pdf_file in pdf_files:
        print(f"  [PDF] Loading: {pdf_file.name}")
        pages = extract_text_from_pdf(str(pdf_file))

        chunk_idx = 0
        for page_data in pages:
            chunks = chunk_text(page_data["text"], chunk_size, chunk_overlap)
            for chunk in chunks:
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": page_data["source"],
                        "page": page_data["page"],
                        "chunk_id": chunk_idx,
                        "path": page_data["path"],
                    },
                )
                all_documents.append(doc)
                chunk_idx += 1

        print(f"     OK {pdf_file.name}: {len(pages)} pages -> {chunk_idx} chunks")

    print(f"\n  Total documents loaded: {len(all_documents)} chunks from {len(pdf_files)} PDFs")
    return all_documents


def get_raw_text(pdf_dir: str) -> str:
    """Return all PDF text concatenated — used for LightRAG & GraphRAG ingestion."""
    pdf_dir_path = Path(pdf_dir)
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    all_text = []

    for pdf_file in pdf_files:
        pages = extract_text_from_pdf(str(pdf_file))
        file_text = "\n\n".join(p["text"] for p in pages)
        all_text.append(f"=== {pdf_file.name} ===\n\n{file_text}")

    return "\n\n\n".join(all_text)
