"""
utils.py

Helper functions shared across the app.
Kept small on purpose — a real student project doesn't over-engineer utilities.
"""

from typing import List


def compute_confidence(similarity_scores: List[float]) -> dict:
    """
    Takes a list of cosine similarity scores from the retriever
    and returns a human-readable confidence label + the average score.

    Thresholds:
      - avg < 0.50  => low
      - avg < 0.75  => medium
      - avg >= 0.75 => high

    These are rough heuristics tuned for sentence-transformer embeddings.
    """
    if not similarity_scores:
        return {"label": "low", "score": 0.0}

    avg = sum(similarity_scores) / len(similarity_scores)

    if avg >= 0.75:
        label = "high"
    elif avg >= 0.50:
        label = "medium"
    else:
        label = "low"

    return {"label": label, "score": round(avg, 3)}


def format_source_chunks(chunks: List[dict]) -> List[dict]:
    """
    Strips down raw LangChain Document objects to only what the
    frontend actually needs — text preview + clause metadata.
    """
    formatted = []
    for chunk in chunks:
        # LangChain Document has .page_content and .metadata
        formatted.append({
            "text_preview": chunk.page_content[:300],  # show first 300 chars
            "clause_number": chunk.metadata.get("clause_number", "Unknown"),
            "page_number": chunk.metadata.get("page_number", "?"),
            "char_start": chunk.metadata.get("char_start", 0),
        })
    return formatted


def clean_text(raw: str) -> str:
    """
    Basic cleanup on text extracted from PDFs.
    PDF extraction often produces weird spacing, repeated newlines, etc.
    """
    import re
    # Collapse multiple blank lines into one
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    # Remove weird non-printable characters that sneak in from PDFs
    raw = re.sub(r"[^\x00-\x7F]+", " ", raw)
    # Normalize spacing
    raw = re.sub(r" {2,}", " ", raw)
    return raw.strip()
