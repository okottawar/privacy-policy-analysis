# PrivacyLens

**A RAG-powered privacy policy risk analyzer.**

Paste any privacy policy URL and get a structured risk report — scored across six categories, grounded in evidence retrieved directly from the document. No summaries from memory. No hallucinated findings.

🔗 **Live demo:** `https://okottawar.github.io/privacy-policy-analyzer`

---

## What it does

Most people never read privacy policies. PrivacyLens makes them legible — it fetches a policy, breaks it into chunks, retrieves the most relevant clauses for each risk category, and asks an LLM to reason only over what it actually found.

The output is a structured report covering:

| Category | What it examines |
|---|---|
| Data Collection | What personal data is gathered and why |
| Third-Party Sharing | Whether data is sold or shared with advertisers |
| Data Retention | How long data is kept, and under what conditions |
| User Rights | Access, deletion, and portability controls |
| Tracking & Cookies | Behavioural tracking, fingerprinting, ad targeting |
| Consent Mechanisms | How consent is obtained and whether opt-out exists |

Each category gets a 0–10 risk score, a list of red flags, positive indicators, and the exact policy excerpts that produced the finding.

---

## How it works

The system is built around a retrieval-augmented generation (RAG) pipeline. The LLM never reasons from memory — it only sees chunks retrieved from the actual document.

```
Policy URL
   │
   ▼
Fetch & clean                   requests + trafilatura
   │
   ▼
Section extraction              heading heuristics
   │
   ▼
Hierarchical chunking           LangChain RecursiveCharacterTextSplitter
   │                            800 tokens, 150 token overlap
   ▼
TF-IDF index                    scikit-learn, bigram features
   │
   ▼
Per-category retrieval          cosine similarity, top-5 chunks per query
   │
   ▼
LLM reasoning                   Gemini 1.5 Flash, JSON-only output
   │
   ▼
Heuristic score adjustment      keyword signal layer over LLM score
   │
   ▼
Structured risk report
```

The scoring is intentionally not left entirely to the LLM. A keyword heuristic layer adjusts the LLM-generated score up or down based on known high-risk phrases ("may share with third parties", "retain indefinitely") and low-risk signals ("right to erasure", "you may withdraw consent"). This makes the scoring more reproducible and less sensitive to LLM phrasing variation.

### Why TF-IDF instead of dense embeddings

The original design used FAISS with `sentence-transformers/all-MiniLM-L6-v2` for dense vector retrieval. During deployment, this exceeded Render's free tier memory ceiling (512MB) — PyTorch and the transformer weights alone consume ~450MB at idle.

Privacy policy text is keyword-dense legal language. Sparse retrieval with TF-IDF bigrams performs comparably to dense embeddings for this domain, while using ~5MB of memory instead of ~450MB. The architectural pattern — chunk, index, retrieve, reason — is identical either way.

---

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────────┐
│   Frontend                  │         │   Backend (FastAPI on Render)     │
│   GitHub Pages              │         │                                   │
│                             │  POST   │  app/                             │
│   Pure HTML + JS            │ ──────► │  ├── routers/analyze.py          │
│   No API key exposed        │         │  ├── services/                    │
│   TF-IDF chunk explorer     │ ◄────── │  │   ├── retrieval.py            │
│                             │  JSON   │  │   ├── chunking.py             │
└─────────────────────────────┘         │  │   └── llm_service.py         │
                                        │  └── models/schemas.py           │
                                        │                                   │
                                        │  GEMINI_API_KEY → env var only    │
                                        └──────────────────────────────────┘
```

The API key never touches the frontend. It lives only in Render's environment variables and is loaded at startup. CORS is locked to the GitHub Pages origin.

---

## Project structure

```
privacy-policy-analyzer/
│
├── frontend/
│   └── index.html              # Entire frontend — single file, no build step
│
└── backend/
    ├── requirements.txt
    ├── render.yaml
    ├── .env.example
    └── app/
        ├── main.py             # FastAPI app, CORS middleware
        ├── routers/
        │   └── analyze.py      # POST /api/v1/analyze — pipeline orchestration
        ├── services/
        │   ├── retrieval.py    # URL fetching, HTML cleaning, section extraction
        │   ├── chunking.py     # LangChain chunking + TF-IDF index + retrieval
        │   └── llm_service.py  # Gemini prompting, heuristic scoring, executive summary
        └── models/
            └── schemas.py      # Pydantic request/response validation
```

---

## API

`POST /api/v1/analyze`

```json
{
  "url": "https://policies.google.com/privacy"
}
```

```json
{
  "url": "https://policies.google.com/privacy",
  "overall": { "score": 6.4, "label": "Moderate Risk" },
  "executive_summary": "...",
  "total_chunks": 138,
  "total_sections": 21,
  "findings": [
    {
      "risk_category": "Third Party Sharing",
      "risk_score": 8,
      "summary": "The policy permits broad sharing with advertising partners...",
      "key_findings": ["..."],
      "red_flags": ["We may share information with advertising networks..."],
      "positive_indicators": ["You may opt out of personalised advertising..."],
      "evidence_chunks": [
        { "section": "Sharing your information", "content": "...", "similarity_score": 0.71 }
      ],
      "score_method": "llm+heuristic"
    }
  ]
}
```

Interactive docs available at `/docs` when running locally.

---

## Running locally

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/docs` for the Swagger UI, or point `BACKEND_URL` in `frontend/index.html` to `http://localhost:8000` and open the frontend with a local server.

---

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | HTML + JS | Single file, no framework, no build step |
| Backend | FastAPI + Pydantic | Async, typed, auto-documented |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | Section-aware, configurable overlap |
| Retrieval | scikit-learn TF-IDF + cosine similarity | Chosen over FAISS to fit free-tier memory |
| LLM | Gemini 1.5 Flash | JSON-mode prompting, structured output |
| Parsing | trafilatura + BeautifulSoup | Main-content extraction, clutter removal |
| Hosting | GitHub Pages + Render | Both free tiers |

---

## Disclaimer

Educational portfolio project. Generated findings are heuristic-based and should not be interpreted as legal or regulatory conclusions.