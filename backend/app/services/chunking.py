"""
Chunking & Embedding Pipeline
Hierarchical chunking based on section boundaries + semantic overlap.
Embeddings via sentence-transformers, stored in FAISS.
Runs on Hugging Face Spaces (16GB RAM) — no memory constraints.
"""

import uuid
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


# Singleton embedding model — loaded once at first request, reused after
_embedding_model: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy-load the embedding model on first use."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model


def chunk_sections(sections: list[dict], chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """
    Hierarchical chunking:
    1. Respect section boundaries (coarse split)
    2. Recursively split oversized sections (fine split)
    Returns enriched chunk dicts with metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for section in sections:
        sub_chunks = splitter.split_text(section["content"])
        for i, text in enumerate(sub_chunks):
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "section": section["section"],
                "content": text,
                "chunk_index": i,
                "total_chunks_in_section": len(sub_chunks),
            })

    return chunks


def build_vector_store(chunks: list[dict]) -> FAISS:
    """
    Embed all chunks and build a FAISS vector store.
    Metadata (section, chunk_id) stored alongside vectors.
    """
    embeddings = get_embeddings()

    texts = [c["content"] for c in chunks]
    metadatas = [
        {
            "section": c["section"],
            "chunk_id": c["chunk_id"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    return FAISS.from_texts(texts, embeddings, metadatas=metadatas)


def retrieve_relevant_chunks(
    vector_store: FAISS,
    query: str,
    k: int = 5,
) -> list[dict]:
    """
    Retrieve top-k semantically relevant chunks for a query.
    Always returns up to k results — no threshold filtering.
    FAISS L2 distance is converted to a 0-1 similarity score for display only.
    """
    results_with_scores = vector_store.similarity_search_with_score(query, k=k)

    retrieved = []
    for doc, score in results_with_scores:
        # Convert L2 distance to similarity score (display only — not used for filtering)
        similarity = float(1 / (1 + score))
        retrieved.append({
            "content": doc.page_content,
            "section": doc.metadata.get("section", "Unknown"),
            "chunk_id": doc.metadata.get("chunk_id", ""),
            "similarity_score": round(similarity, 4),
        })

    retrieved.sort(key=lambda x: x["similarity_score"], reverse=True)
    return retrieved
