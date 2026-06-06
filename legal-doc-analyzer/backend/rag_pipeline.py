"""
rag_pipeline.py

Core RAG logic: build a FAISS vector store from document chunks,
then retrieve and answer questions using Groq + LangChain.

Two main classes:
  - RAGPipeline: single-document QA
  - ComparisonPipeline: two-document comparison
"""

import os
from typing import List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from chunker import clause_aware_chunk
from utils import compute_confidence, format_source_chunks, clean_text


# ── Model setup ────────────────────────────────────────────────────────────────

GROQ_MODEL = "llama3-70b-8192"

# HuggingFace model downloaded locally on first run (no API key needed)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Number of chunks to retrieve per query
TOP_K = 4


def _load_embeddings() -> HuggingFaceEmbeddings:
    """
    Load sentence-transformer embeddings.
    This runs locally — no external API call for embeddings.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _load_llm() -> ChatGroq:
    """Load the Groq-hosted LLaMA 3 model."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    return ChatGroq(
        groq_api_key=api_key,
        model_name=GROQ_MODEL,
        temperature=0.1,  # low temp = factual, less creative
    )


# ── System prompt ───────────────────────────────────────────────────────────────

QA_PROMPT_TEMPLATE = """
You are a legal document assistant. Your job is to answer questions strictly based on the
legal document excerpts provided below. Do NOT make up information or use outside knowledge.

If the answer is clearly present in the context, answer directly and cite which clause/section it came from.
If you cannot find the answer in the provided context, say exactly:
"I couldn't find this in the document."

Context (retrieved clauses):
{context}

Question: {question}

Answer:
"""

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=QA_PROMPT_TEMPLATE,
)

COMPARISON_PROMPT_TEMPLATE = """
You are a legal document comparison assistant. You have been given excerpts from two different
legal documents. Answer the comparison question strictly based on the content provided.
If either document doesn't address the question, say so clearly.

Document A excerpts:
{context_a}

Document B excerpts:
{context_b}

Comparison question: {question}

Answer:
"""

COMPARISON_PROMPT = PromptTemplate(
    input_variables=["context_a", "context_b", "question"],
    template=COMPARISON_PROMPT_TEMPLATE,
)

SUGGEST_PROMPT_TEMPLATE = """
You are looking at a legal document. Based on the first part of the document shown below,
generate exactly 4 useful questions a non-lawyer might want to ask about this agreement.
Return ONLY the questions, one per line, no numbering, no extra text.

Document excerpt:
{context}

Questions:
"""

SUGGEST_PROMPT = PromptTemplate(
    input_variables=["context"],
    template=SUGGEST_PROMPT_TEMPLATE,
)


# ── Main RAG Pipeline ───────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Handles a single uploaded document.
    Build the vector store from the PDF text, then answer questions.
    """

    def __init__(self):
        self.vectorstore = None
        self.raw_chunks = []
        self.embeddings = _load_embeddings()
        self.llm = _load_llm()

    def ingest(self, pdf_text: str) -> int:
        """
        Process a PDF's extracted text:
        1. Clean the text
        2. Chunk it clause-by-clause
        3. Build a FAISS vector store

        Returns the number of chunks created.
        """
        cleaned = clean_text(pdf_text)
        self.raw_chunks = clause_aware_chunk(cleaned)

        # Convert to LangChain Document objects
        documents = [
            Document(
                page_content=chunk["text"],
                metadata=chunk["metadata"],
            )
            for chunk in self.raw_chunks
            if chunk["text"].strip()  # skip empty chunks
        ]

        if not documents:
            raise ValueError("No text could be extracted from the PDF.")

        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        return len(documents)

    def answer(self, question: str) -> dict:
        """
        Answer a question using MMR retrieval + LLaMA 3 via Groq.

        MMR (Maximum Marginal Relevance) retrieves diverse chunks instead of
        just the top-4 most similar ones, which helps avoid getting 4 chunks
        that all say the same thing.
        """
        if self.vectorstore is None:
            raise ValueError("No document loaded. Upload a PDF first.")

        # MMR retrieval: balance relevance and diversity
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": TOP_K,
                "fetch_k": TOP_K * 3,  # fetch more, then pick diverse top-k
                "lambda_mult": 0.7,   # 0 = max diversity, 1 = max relevance
            },
        )

        retrieved_docs = retriever.get_relevant_documents(question)

        # Get similarity scores for confidence — need to run a separate similarity search
        # because MMR doesn't return scores directly
        scored = self.vectorstore.similarity_search_with_score(question, k=TOP_K)
        similarity_scores = [1 - score for _, score in scored]  # FAISS returns L2 distance

        # Build context string from retrieved chunks
        context = "\n\n---\n\n".join(
            [f"[{doc.metadata.get('clause_number', 'Unknown')}]\n{doc.page_content}"
             for doc in retrieved_docs]
        )

        # Run LLM
        chain = LLMChain(llm=self.llm, prompt=QA_PROMPT)
        answer_text = chain.run(context=context, question=question)

        confidence = compute_confidence(similarity_scores)
        sources = format_source_chunks(retrieved_docs)

        return {
            "answer": answer_text.strip(),
            "confidence": confidence,
            "sources": sources,
        }

    def suggest_questions(self) -> List[str]:
        """
        Look at the first few chunks of the document and ask the LLM
        to suggest relevant questions the user might want to ask.
        """
        if not self.raw_chunks:
            return []

        # Use the first 3 chunks as context for suggestions
        sample_text = "\n\n".join(
            [c["text"] for c in self.raw_chunks[:3]]
        )[:2000]  # limit to 2000 chars

        chain = LLMChain(llm=self.llm, prompt=SUGGEST_PROMPT)
        result = chain.run(context=sample_text)

        # Parse the result — one question per line
        questions = [
            line.strip()
            for line in result.strip().split("\n")
            if line.strip() and "?" in line
        ]

        return questions[:4]  # cap at 4


# ── Comparison Pipeline ─────────────────────────────────────────────────────────

class ComparisonPipeline:
    """
    Handles two uploaded documents for comparison questions.
    Builds separate vector stores for each document.
    """

    def __init__(self):
        self.pipeline_a = RAGPipeline()
        self.pipeline_b = RAGPipeline()
        self.llm = _load_llm()

    def ingest_both(self, text_a: str, text_b: str) -> Tuple[int, int]:
        """Ingest two documents. Returns chunk counts for both."""
        count_a = self.pipeline_a.ingest(text_a)
        count_b = self.pipeline_b.ingest(text_b)
        return count_a, count_b

    def compare(self, question: str) -> dict:
        """
        Retrieve relevant chunks from both documents independently,
        then ask the LLM to compare them.
        """
        if self.pipeline_a.vectorstore is None or self.pipeline_b.vectorstore is None:
            raise ValueError("Both documents must be uploaded before comparing.")

        # Retrieve from doc A
        docs_a = self.pipeline_a.vectorstore.similarity_search(question, k=TOP_K)
        context_a = "\n\n".join(
            [f"[{d.metadata.get('clause_number', '?')}]\n{d.page_content}" for d in docs_a]
        )

        # Retrieve from doc B
        docs_b = self.pipeline_b.vectorstore.similarity_search(question, k=TOP_K)
        context_b = "\n\n".join(
            [f"[{d.metadata.get('clause_number', '?')}]\n{d.page_content}" for d in docs_b]
        )

        chain = LLMChain(llm=self.llm, prompt=COMPARISON_PROMPT)
        answer_text = chain.run(
            context_a=context_a,
            context_b=context_b,
            question=question,
        )

        return {
            "answer": answer_text.strip(),
            "sources_a": format_source_chunks(docs_a),
            "sources_b": format_source_chunks(docs_b),
        }
