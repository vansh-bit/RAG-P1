# RAG Legal Doc Analyzer — Interview Prep Guide
*Read this after understanding the code. These are real questions you'll get.*

---

## 1. What is RAG and why did you use it?

**What to say:**
RAG stands for Retrieval-Augmented Generation. Instead of fine-tuning an LLM on legal documents (which is expensive and needs a lot of data), RAG lets the model look up relevant parts of a document at query time. So when someone asks "what's the notice period?", the system retrieves the specific clause about notice periods from a vector store, and passes it to the LLM as context. The LLM answers from that context only — it doesn't rely on what it "memorized" during training.

**Why not just send the whole document to the LLM?**
Token limits and cost. LLaMA 3 has an 8192 token context window. A 20-page contract can easily be 15,000+ tokens. Even if it fit, sending the full doc every question would be slow and hit rate limits. RAG lets us retrieve only the 4 most relevant chunks (~600–800 tokens) and answer from those.

---

## 2. Explain your chunking strategy. Why not use character-based chunking?

**What to say:**
Most RAG tutorials use RecursiveCharacterTextSplitter — split every 500 characters with 50-character overlap. That works for Wikipedia articles, but legal documents have *clause structure*. A clause has a heading ("Clause 4 — Rent"), a body, and exceptions. If you cut it in the middle, you lose context.

My chunker (chunker.py) uses regex to find clause boundaries first:
- Patterns like "Clause X", "Section X", "1.", "RENT AND PAYMENT" (all caps headings)
- If 2 or more boundaries found → split there, each chunk = one clause
- Each chunk carries metadata: clause number, approximate page, character offset

This means when the retriever fetches Clause 4, it gets the complete clause, not half of it. That's a real improvement for legal QA.

If no structure is detected, it falls back to 500-char chunks with 50-char overlap — same as the tutorial approach, but only as a fallback.

---

## 3. What is FAISS and why not use Pinecone or Weaviate?

**What to say:**
FAISS (Facebook AI Similarity Search) is a library for efficient vector similarity search. It runs locally — no cloud service needed. I chose it because:
1. Cost: Pinecone free tier has row limits and requires an account. FAISS is free forever.
2. Simplicity: No network calls for vector search, no rate limits
3. Fits the use case: I'm storing a few hundred vectors per session (one contract). FAISS handles millions — way more than enough.

The tradeoff: FAISS doesn't persist across server restarts. If I wanted persistent storage, I'd save the index to disk with faiss.write_index(). But for a session-based demo, in-memory is fine.

---

## 4. What is MMR and why did you use it instead of similarity search?

**What to say:**
MMR = Maximum Marginal Relevance. Standard similarity search returns the top-K most similar chunks to your query. The problem: if your query is "what is the rent amount?", and 4 clauses all mention rent, you get 4 similar chunks that say the same thing. The LLM gets redundant context.

MMR balances relevance (similarity to query) and diversity (dissimilarity between retrieved results). It picks the next chunk that is both relevant to the query AND different from chunks already selected. The lambda_mult parameter controls this — I set it to 0.7 (more relevance, some diversity).

In practice for legal docs, this means if two clauses both discuss rent, MMR will pick the most relevant one and then look for a different clause for the 2nd, 3rd, 4th results — giving the LLM richer context.

---

## 5. How does the confidence scoring work?

**What to say:**
FAISS similarity search returns a score for each retrieved chunk. I use cosine similarity (by normalizing embeddings).

- Take the top-4 retrieval scores
- Average them
- Map to labels: below 0.5 = low, 0.5 to 0.75 = medium, above 0.75 = high

It's a heuristic, not a statistically rigorous measure. But it gives users a signal — if confidence is "low", the document probably doesn't directly address their question. This matters for legal documents where a wrong answer could have consequences.

---

## 6. Why Groq and not OpenAI?

**What to say:**
Two reasons:
1. Cost: Groq has a free tier with good rate limits. OpenAI GPT-4 costs money.
2. Speed: Groq runs LLaMA 3 on custom hardware (LPU chips). Inference is 5-10x faster than typical GPU servers.

LLaMA 3 70B is competitive with GPT-4 on many benchmarks — for reading comprehension tasks like this, it performs well.

Note: During development I also had to update the model from llama3-70b-8192 to llama-3.3-70b-versatile because Groq deprecated the older one. Good example of actively maintaining the project.

---

## 7. Why HuggingFace sentence-transformers for embeddings, not OpenAI embeddings?

**What to say:**
all-MiniLM-L6-v2 is a small (80MB), fast, locally-running embedding model. OpenAI text-embedding-ada-002 requires an API call for every document chunk during indexing. For a 20-page contract with 40 chunks, that's 40 API calls just to build the index.

The quality tradeoff is real — OpenAI embeddings are better. But for legal document QA where clauses use very specific terminology that appears in both query and document, MiniLM works well enough. Zero cost is also a major reason.

---

## 8. How would you handle scanned PDFs (image-based)?

**What to say:**
Currently I don't — this is in the Known Limitations section. pdfplumber only extracts text from PDFs that have a text layer. A scanned document is just images.

The fix would be:
1. Detect if pdfplumber returns empty text
2. Fall back to pytesseract + pdf2image to convert pages to images and run OCR
3. Feed the OCR'd text into the same chunking pipeline

I didn't implement this to keep the scope manageable.

---

## 9. How would you make this production-ready?

Pick 2-3 of these:
- Persistent storage: Save FAISS indices to disk per user session ID instead of in-memory
- Authentication: JWT tokens so users see only their own documents
- Async processing: Queue long PDF jobs with Celery/Redis, return job ID, poll for status
- Rate limiting: Add limits per IP to avoid Groq API abuse
- Evaluation: Measure retrieval precision with labeled Q&A test pairs

---

## 10. What was the hardest part to build?

**Suggested answer:**
Getting the clause chunking regex right. Legal documents use inconsistent formatting — some write "Clause 1:", some write "1.", some use all-caps headings. I tested against sample rental agreements and kept adding patterns.

Also hit a Python 3.11 regex bug — inline (?i) flags can't appear mid-pattern when patterns are joined with |. Had to move the flag to re.compile(..., re.IGNORECASE). That was a good debugging exercise.

---

## Quick concept definitions (rapid-fire questions)

| Term | One-line answer |
|------|----------------|
| Vector embedding | A list of numbers (384 floats) that captures the semantic meaning of text |
| Vector store | A database optimized for similarity search on embeddings |
| Semantic search | Find documents by meaning, not keyword matching |
| Cosine similarity | How aligned two vectors are — 1.0 = identical meaning, 0 = unrelated |
| LangChain | Python library that chains together LLMs, retrievers, and prompts |
| Context window | Max tokens an LLM can process at once |
| Temperature | Controls randomness — 0.0 = deterministic, 1.0 = creative |
| Hallucination | LLM confidently stating something not in the source document |
| System prompt | Instructions given to the LLM before the user's message |
| MMR | Maximum Marginal Relevance — diverse retrieval to avoid redundant chunks |
| pdfplumber | Python library to extract text from PDF files |
| FastAPI | Python async web framework — auto-generates /docs endpoint |

---

## Things to say you'd improve next

> "The comparison feature is the weakest part. It retrieves from two vector stores independently and asks the LLM to compare. A better approach would be finding semantically equivalent clauses in both docs first, then comparing those matched pairs directly."

> "I'd add an evaluation pipeline using labeled question-answer pairs from sample rental agreements to measure retrieval precision@4."
