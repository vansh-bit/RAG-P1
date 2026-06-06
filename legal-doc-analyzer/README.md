# Legal Document Analyzer

A RAG (Retrieval-Augmented Generation) tool that lets you upload Indian rental agreements or any legal contract as a PDF and ask questions about it in plain English. Built as an AI layer on top of my earlier project, RentEase.

---

## What it does

Upload a legal PDF → the system splits it into clauses → embeds them locally → you ask questions → LLaMA 3 (via Groq) answers using only the actual document content. No hallucination. Sources shown for every answer.

---

## Tech stack

- **Backend**: Python, FastAPI
- **RAG**: LangChain, FAISS (local vector store — no paid DB)
- **LLM**: Groq API (llama3-70b-8192) — free tier is enough
- **Embeddings**: HuggingFace `all-MiniLM-L6-v2` — runs locally, no API key
- **Frontend**: React.js, plain CSS

---

## How to run locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a .env file or just export the variable
export GROQ_API_KEY=your_groq_key_here

uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. You can check `http://localhost:8000/health` to confirm.

### Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at `http://localhost:3000`. The API URL defaults to `http://localhost:8000`. If your backend is on a different URL (e.g., HuggingFace Spaces), set `REACT_APP_API_URL` in a `.env` file.

---

## How the clause-aware chunking works

Most basic RAG tutorials chunk documents by character count (e.g., every 500 characters). The problem with legal docs is that a single clause can span 300–800 characters, so dumb chunking cuts a clause in half and the retriever gets incomplete context.

My chunker (`chunker.py`) first scans the document for regex patterns matching "Clause X", "Section X", numbered headings like "1.", "2.", and ALL CAPS section titles. If it finds at least 2 such boundaries, it splits the document there — each chunk maps to exactly one legal clause. The metadata (clause number, approximate page number, character offset) is stored with each chunk so the frontend can show exactly which clause was used.

If the document has no visible clause structure (some scanned-and-OCR'd PDFs look like walls of text), it falls back to 500-character chunks with 50-character overlap so context isn't lost at boundaries.

---

## Features

1. **PDF upload** — drag & drop or click to select
2. **Clause-aware chunking** — splits on legal section boundaries, not arbitrary character counts
3. **Question answering** — answer comes with source clause highlighted
4. **Confidence indicator** — low/medium/high based on retrieval similarity score
5. **Document comparison** — upload two contracts and ask "which has a longer notice period"
6. **Suggested questions** — auto-generated after upload based on document content

---

## Deployment

- **Backend**: HuggingFace Spaces (Docker-free — just push files + add `GROQ_API_KEY` as a secret)
- **Frontend**: Vercel (just connect the GitHub repo, set `REACT_APP_API_URL` to your HF Spaces URL)

---

## Known limitations

- **Scanned/image PDFs don't work** — pdfplumber can only extract text from text-layer PDFs. If someone used a scanner, the extraction will fail. A future fix would be adding Tesseract OCR as a fallback.
- **No persistent state** — every server restart clears the loaded document. This is intentional to keep things simple, but it means you have to re-upload if the Spaces instance cold-starts.
- **Embeddings download on first run** — `all-MiniLM-L6-v2` (~90MB) is downloaded from HuggingFace the first time. On HF Spaces this is fine; locally it needs a good connection.
- **Groq rate limits** — free tier has RPM limits. If you send many questions quickly you'll hit a 429. Just wait a minute.
- **Long documents are slow** — a 50-page contract takes 10-15 seconds to embed locally on CPU. Not a problem for typical 5-10 page rental agreements.
- **Comparison feature is basic** — it runs two independent retrieval searches and asks the LLM to compare. It's not doing true semantic alignment between the two documents.
- **No memory across questions** — each question is answered independently. The LLM doesn't remember what it said in the previous turn.
