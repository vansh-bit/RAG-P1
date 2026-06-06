"""
main.py

FastAPI server for the legal document analyzer.
All state (vector stores, pipeline objects) is kept in memory per session.
No database, no auth — just a straightforward API.

Endpoints:
  POST /upload         — upload one PDF, get back suggested questions
  POST /ask            — ask a question about the uploaded PDF
  POST /upload-compare — upload two PDFs for comparison
  POST /compare        — ask a comparison question
  GET  /health         — simple health check
"""

import io
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pdfplumber

from rag_pipeline import RAGPipeline, ComparisonPipeline

app = FastAPI(title="Legal Document Analyzer API")

# Allow the React dev server to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state — resets when the server restarts (intentional for this project)
_pipeline: RAGPipeline = None
_comparison_pipeline: ComparisonPipeline = None


# ── Request / Response models ───────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF file using pdfplumber.
    pdfplumber handles most Indian rental agreement PDFs well.
    """
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    if not text_parts:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the PDF. It might be a scanned image PDF.",
        )

    return "\n\n".join(text_parts)


# ── Routes ───────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Legal doc analyzer is running"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF. Extracts text, chunks it, builds the vector store,
    and returns auto-suggested questions.
    """
    global _pipeline

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    pdf_text = _extract_pdf_text(file_bytes)

    _pipeline = RAGPipeline()
    chunk_count = _pipeline.ingest(pdf_text)

    # Generate suggested questions based on doc content
    suggested = _pipeline.suggest_questions()

    return {
        "message": "Document uploaded and indexed successfully.",
        "filename": file.filename,
        "chunk_count": chunk_count,
        "suggested_questions": suggested,
    }


@app.post("/ask")
async def ask_question(body: QuestionRequest):
    """
    Ask a question about the currently loaded document.
    Returns the answer, confidence level, and source clauses used.
    """
    global _pipeline

    if _pipeline is None:
        raise HTTPException(status_code=400, detail="No document loaded. Upload a PDF first.")

    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = _pipeline.answer(body.question)
    return result


@app.post("/upload-compare")
async def upload_for_comparison(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    """
    Upload two PDFs for side-by-side comparison.
    """
    global _comparison_pipeline

    for f in [file_a, file_b]:
        if not f.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    bytes_a = await file_a.read()
    bytes_b = await file_b.read()

    text_a = _extract_pdf_text(bytes_a)
    text_b = _extract_pdf_text(bytes_b)

    _comparison_pipeline = ComparisonPipeline()
    count_a, count_b = _comparison_pipeline.ingest_both(text_a, text_b)

    return {
        "message": "Both documents indexed successfully.",
        "doc_a": {"filename": file_a.filename, "chunks": count_a},
        "doc_b": {"filename": file_b.filename, "chunks": count_b},
    }


@app.post("/compare")
async def compare_documents(body: QuestionRequest):
    """
    Ask a comparison question across two uploaded documents.
    """
    global _comparison_pipeline

    if _comparison_pipeline is None:
        raise HTTPException(
            status_code=400,
            detail="No documents loaded for comparison. Use /upload-compare first.",
        )

    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = _comparison_pipeline.compare(body.question)
    return result
