"""
chunker.py

Custom clause-aware chunker for legal documents.
Instead of blindly splitting by character count, we first try to identify
clause/section boundaries using regex. If the document has no clear structure,
we fall back to character-based chunking with overlap.
"""

import re
from typing import List, Dict, Any


# Patterns that typically mark the start of a new clause or section in legal docs
CLAUSE_PATTERNS = [
    r"(?i)^clause\s+\d+[\.\:]",          # "Clause 1." or "Clause 1:"
    r"(?i)^section\s+\d+[\.\:]",         # "Section 1." or "Section 1:"
    r"(?i)^article\s+\d+[\.\:]",         # "Article 1." or "Article 1:"
    r"^\d+\.\s+[A-Z]",                   # "1. Something" — numbered heading
    r"^\d+\)\s+[A-Z]",                   # "1) Something"
    r"^[A-Z][A-Z\s]{3,}$",              # ALL CAPS heading like "RENT AND PAYMENT"
    r"(?i)^schedule\s+[A-Z\d]+",         # "Schedule A", "Schedule 1"
    r"(?i)^appendix\s+[A-Z\d]+",         # "Appendix A"
]

COMBINED_PATTERN = re.compile("|".join(CLAUSE_PATTERNS), re.MULTILINE)

# Fallback chunking settings
FALLBACK_CHUNK_SIZE = 500
FALLBACK_OVERLAP = 50


def _attach_metadata(text: str, clause_number: str, chunk_index: int, char_start: int) -> Dict[str, Any]:
    """
    Wrap a text chunk with metadata so the retrieval layer knows
    where in the document each chunk came from.
    """
    return {
        "text": text.strip(),
        "metadata": {
            "clause_number": clause_number,
            "chunk_index": chunk_index,
            "char_start": char_start,
            # page_number is a best-effort estimate — PDFs parsed as plain text
            # lose real page info, so we approximate based on char position
            "page_number": max(1, char_start // 3000 + 1),
        },
    }


def clause_aware_chunk(full_text: str) -> List[Dict[str, Any]]:
    """
    Main chunking function.

    1. Try to find clause/section boundaries using regex.
    2. If we find at least 2 boundaries, use clause-based splitting.
    3. Otherwise, fall back to character-based chunking.

    Returns a list of dicts, each with 'text' and 'metadata' keys.
    """
    matches = list(COMBINED_PATTERN.finditer(full_text))

    if len(matches) >= 2:
        return _clause_based_split(full_text, matches)
    else:
        return _character_based_split(full_text)


def _clause_based_split(full_text: str, matches) -> List[Dict[str, Any]]:
    """
    Split the document at each regex match boundary.
    Each resulting segment is one chunk with its clause label as metadata.
    """
    chunks = []
    boundaries = [(m.start(), m.group().strip()) for m in matches]

    for i, (start, clause_label) in enumerate(boundaries):
        # End of this clause = start of next clause (or end of doc)
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(full_text)
        segment = full_text[start:end]

        # If a single clause is very long, sub-split it so embeddings stay meaningful
        if len(segment) > 1500:
            sub_chunks = _character_based_split(segment, base_char_offset=start)
            for j, sub in enumerate(sub_chunks):
                sub["metadata"]["clause_number"] = clause_label
                sub["metadata"]["chunk_index"] = len(chunks)
                chunks.append(sub)
        else:
            chunks.append(_attach_metadata(segment, clause_label, len(chunks), start))

    return chunks


def _character_based_split(text: str, base_char_offset: int = 0) -> List[Dict[str, Any]]:
    """
    Fallback: split by character count with overlap so context isn't lost
    at chunk boundaries.
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + FALLBACK_CHUNK_SIZE
        segment = text[start:end]
        char_start = base_char_offset + start

        chunks.append(
            _attach_metadata(segment, f"chunk-{chunk_index}", chunk_index, char_start)
        )

        chunk_index += 1
        # Move forward but keep some overlap so we don't lose context
        start += FALLBACK_CHUNK_SIZE - FALLBACK_OVERLAP

    return chunks
