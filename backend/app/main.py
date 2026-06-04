"""
Privacy Policy Risk Analyzer — FastAPI Backend
Gemini API key is loaded from GEMINI_API_KEY environment variable.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analyze

app = FastAPI(
    title="Privacy Policy Risk Analyzer",
    description="RAG-based privacy policy analysis using LangChain, FAISS, and Google Gemini.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In production, restrict this to your GitHub Pages domain:
# e.g. "https://YOUR-USERNAME.github.io"
# During local dev, localhost origins are also allowed.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])


@app.get("/")
def root():
    return {"status": "ok", "message": "Privacy Policy Risk Analyzer API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
