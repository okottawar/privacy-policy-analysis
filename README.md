# PrivacyLens — Privacy Policy Risk Analyzer

> Portfolio project demonstrating production RAG concepts: LangChain + FAISS + Gemini 1.5 Flash.
> Users just enter a URL — no API key required on their end.

**Frontend (GitHub Pages):** `https://okottawar.github.io/privacy-policy-analyzer`
**Backend (Render):** `https://YOUR-APP-NAME.onrender.com`

---

## Architecture

```
[User: enters URL]
        │
        ▼
[Frontend — GitHub Pages]
  Pure HTML/JS
  POST { url } → Backend
        │
        ▼
[Backend — Render (FastAPI)]
  GEMINI_API_KEY loaded from env
        │
  ┌─────┴──────────────────────┐
  │  1. Fetch & clean policy   │  requests + trafilatura
  │  2. Extract sections       │  heading heuristics
  │  3. Chunk (800t, 150 ovlp) │  LangChain RecursiveTextSplitter
  │  4. Embed + FAISS index    │  all-MiniLM-L6-v2
  │  5. Retrieve (per category)│  FAISS similarity_search
  │  6. LLM reasoning          │  Gemini 1.5 Flash
  │  7. Heuristic score adjust │  keyword signals
  │  8. Executive summary      │  Gemini 1.5 Flash
  └─────┬──────────────────────┘
        │
        ▼
  JSON response → Frontend renders report
```

---

## Project Structure

```
privacy-policy-analyzer/
├── frontend/
│   └── index.html              # GitHub Pages app — calls backend, no API key exposed
│
├── backend/
│   ├── render.yaml             # Render deployment config
│   ├── requirements.txt
│   ├── .env.example            # Copy to .env for local dev
│   └── app/
│       ├── main.py             # FastAPI app + CORS config
│       ├── routers/
│       │   └── analyze.py      # POST /api/v1/analyze
│       ├── services/
│       │   ├── retrieval.py    # Fetch + parse + clean policy text
│       │   ├── chunking.py     # LangChain chunking + FAISS pipeline
│       │   └── llm_service.py  # Gemini reasoning + heuristic scoring
│       └── models/
│           └── schemas.py      # Pydantic request/response models
│
└── README.md
```

---

## Deployment Guide

### Step 1 — Get a free Gemini API key

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key** — no credit card needed
3. Copy the key (starts with `AIzaSy…`)

---

### Step 2 — Deploy the backend to Render

1. Push this repo to GitHub (include the `backend/` folder)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Root directory:** `backend`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GEMINI_API_KEY` → your key
   - `ALLOWED_ORIGINS` → `https://YOUR-USERNAME.github.io` (add after step 3)
6. Click **Deploy** — Render gives you a URL like `https://privacylens-api.onrender.com`

---

### Step 3 — Deploy the frontend to GitHub Pages

1. Open `frontend/index.html`
2. Find this line near the top of the `<script>` section:
   ```js
   const BACKEND_URL = 'https://YOUR-APP-NAME.onrender.com';
   ```
   Replace with your actual Render URL.
3. Push to GitHub:
   ```bash
   git add .
   git commit -m "feat: set backend URL"
   git push
   ```
4. Go to repo **Settings → Pages**
   - Source: `Deploy from a branch`
   - Branch: `main` | Folder: `/frontend`
   - Save
5. Site goes live at `https://YOUR-USERNAME.github.io/privacy-policy-analyzer`

---

### Step 4 — Update CORS on Render

Go back to your Render service → **Environment** → update:
```
ALLOWED_ORIGINS=https://YOUR-USERNAME.github.io,http://localhost:5500
```
Render redeploys automatically.

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in your key
cp .env.example .env

uvicorn app.main:app --reload --port 8000
# Swagger UI → http://localhost:8000/docs
```

### Frontend

Point the `BACKEND_URL` in `index.html` to `http://localhost:8000`, then open the file with any
live-server (VS Code Live Server, `python -m http.server`, etc.).

---

## Test Policies (reliable URLs)

| Company | URL |
|---|---|
| Google | `https://policies.google.com/privacy` |
| Apple | `https://www.apple.com/legal/privacy/en-ww/` |
| GitHub | `https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement` |
| Wikipedia | `https://foundation.wikimedia.org/wiki/Privacy_policy` |

If a site blocks the backend fetcher, use the **Paste Text** tab.

---

## API Reference

### `POST /api/v1/analyze`

**Request:**
```json
{
  "url": "https://policies.google.com/privacy",
  "policy_text": null
}
```

**Response:**
```json
{
  "url": "https://policies.google.com/privacy",
  "overall": { "score": 6.4, "label": "Moderate Risk", "color": "amber" },
  "executive_summary": "...",
  "total_chunks": 138,
  "total_sections": 21,
  "findings": [
    {
      "risk_category": "Third Party Sharing",
      "risk_score": 8,
      "summary": "...",
      "key_findings": ["..."],
      "red_flags": ["..."],
      "positive_indicators": ["..."],
      "evidence": ["..."],
      "evidence_chunks": [
        { "content": "...", "section": "...", "similarity_score": 0.74 }
      ],
      "score_method": "llm+heuristic"
    }
  ]
}
```

---

## Engineering Concepts Demonstrated

| Concept | Where |
|---|---|
| RAG pipeline | `chunking.py` → `analyze.py` |
| Semantic chunking | `LangChain RecursiveCharacterTextSplitter` |
| Dense vector retrieval | `FAISS` + `sentence-transformers` |
| Evidence grounding | LLM prompt contains only retrieved chunks |
| Deterministic scoring | Keyword heuristics in `llm_service.py` |
| Structured prompting | JSON-only system prompt, strict schema |
| Secret management | `GEMINI_API_KEY` env var, never in code |
| CORS security | Origin whitelist via `ALLOWED_ORIGINS` env var |
| Modular backend | Separate services: retrieval / chunking / llm |

---

## Disclaimer

Educational portfolio project. Findings are heuristic-based and not legal advice.
