---
title: PrivacyLens API
emoji: 🔍
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
---

# PrivacyLens — Privacy Policy Risk Analyzer API

FastAPI backend for PrivacyLens. Analyzes privacy policies using a RAG pipeline:
LangChain chunking → FAISS vector search → Gemini 1.5 Flash reasoning.

## Endpoints

- `GET /` — health check
- `GET /health` — health check  
- `POST /api/v1/analyze` — analyze a privacy policy
- `GET /docs` — interactive Swagger UI

## Environment Variables (set as Space Secrets)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins e.g. `https://username.github.io` |

## Usage

```json
POST /api/v1/analyze
{
  "url": "https://policies.google.com/privacy"
}
```
