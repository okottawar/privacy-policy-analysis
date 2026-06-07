"""
Chunking & Retrieval Pipeline
Hierarchical chunking + TF-IDF cosine similarity retrieval via scikit-learn.
Replaces FAISS + sentence-transformers to stay within Render free tier memory (512MB).
TF-IDF is well-suited to privacy policy text: keyword-dense legal language.
"""

import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


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


class TFIDFIndex:
    """
    Lightweight in-memory TF-IDF index.
    Replaces FAISS — no model weights, no GPU, <5MB RAM.
    """

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        texts = [c["content"] for c in chunks]

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),      # unigrams + bigrams for better legal text matching
            max_features=20000,
            sublinear_tf=True,       # log normalization reduces impact of high-freq terms
        )
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 5, threshold: float = 0.05) -> list[dict]:
        """Return top-k chunks most similar to query, above threshold."""
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix).flatten()

        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= threshold:
                results.append({
                    "content": self.chunks[idx]["content"],
                    "section": self.chunks[idx]["section"],
                    "chunk_id": self.chunks[idx]["chunk_id"],
                    "similarity_score": round(score, 4),
                })

        return results


def build_index(chunks: list[dict]) -> TFIDFIndex:
    """Build a TF-IDF index from chunks."""
    return TFIDFIndex(chunks)


def retrieve_relevant_chunks(
    index: TFIDFIndex,
    query: str,
    k: int = 5,
) -> list[dict]:
    """Retrieve top-k relevant chunks for a query."""
    return index.search(query, k=k)
