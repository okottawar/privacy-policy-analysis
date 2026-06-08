"""
/api/v1/analyze — Main analysis endpoint.
Orchestrates: fetch → chunk → embed → retrieve → reason → score → report
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.retrieval import fetch_policy, extract_sections
from app.services.chunking import chunk_sections, build_vector_store, retrieve_relevant_chunks
from app.services.llm_service import (
    analyze_risk_category,
    compute_overall_score,
    generate_executive_summary,
    RISK_QUERIES,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_policy(request: AnalyzeRequest):
    """
    Full RAG pipeline:
    1. Fetch & clean the privacy policy
    2. Extract sections and chunk the document
    3. Build FAISS vector store with sentence-transformer embeddings
    4. For each risk category: retrieve relevant chunks + run LLM reasoning
    5. Aggregate scores and generate executive summary
    """

    # ── Step 1: Fetch or use provided text ───────────────────────────────────
    try:
        raw_text = request.policy_text if request.policy_text else fetch_policy(str(request.url))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to fetch policy: {e}")

    if len(raw_text) < 200:
        raise HTTPException(status_code=422, detail="Policy text too short to analyze.")

    # ── Step 2: Parse sections + chunk ───────────────────────────────────────
    sections = extract_sections(raw_text)
    chunks = chunk_sections(sections, chunk_size=800, overlap=150)

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract text chunks.")

    # ── Step 3: Build FAISS vector store ─────────────────────────────────────
    try:
        vector_store = build_vector_store(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # ── Step 4: Retrieve + reason per category ────────────────────────────────
    findings = []
    for category, query in RISK_QUERIES.items():
        relevant = retrieve_relevant_chunks(vector_store, query, k=5)
        finding = analyze_risk_category(
            category_name=category.replace("_", " ").title(),
            retrieved_chunks=relevant,
        )
        findings.append(finding)

    # ── Step 5: Aggregate + executive summary ─────────────────────────────────
    overall = compute_overall_score(findings)
    executive_summary = generate_executive_summary(findings, overall)

    return AnalyzeResponse(
        url=str(request.url),
        overall=overall,
        findings=findings,
        total_chunks=len(chunks),
        total_sections=len(sections),
        executive_summary=executive_summary,
    )
