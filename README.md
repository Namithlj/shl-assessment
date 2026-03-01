# SHL Assessment Recommendation System

This project crawls the SHL product catalog, builds a retrieval index over **Individual Test Solutions**, and serves a web API + frontend that recommends **5–10** relevant assessments for a natural-language query, JD text, or JD URL. It also enforces **balanced recommendations** (K vs P) when a query spans both technical and behavioral domains.

## What’s Included
- **Crawler** that scrapes the SHL product catalog and extracts title, URL, category, duration, test type.
- **Normalization pipeline** to label Individual vs Pre-packaged solutions and add `test_type`.
- **Embedding + retrieval** (SentenceTransformers + NearestNeighbors).
- **API** with `/health` and `/recommend` endpoints.
- **Frontend** (served from `/`) for quick testing.
- **Evaluation scripts/data** (train labels and submission CSV format support).

---

## Quick Start (Windows PowerShell)

1. Create a virtualenv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Crawl the SHL catalog (saves raw data):

```powershell
python crawler\scrape_shl.py --out data/products.json
```

3. Normalize the catalog (filters Individual Test Solutions and adds test type):

```powershell
python crawler\normalize_products.py --in data/products.json --out data/normalized_products
```

4. Build embeddings + retrieval index:

```powershell
python crawler\embed_and_index.py --in data/normalized_products.json --out data
```

5. Run API + Frontend (local):

```powershell
python -m api.server
# open http://127.0.0.1:8181/ in your browser
```

---

## API

**Live demo:** https://shl-assessment-cbme.onrender.com

### Health Check
`GET /health`

**Response:**
```json
{ "status": "ok" }
```

### Recommendation
`POST /recommend`

**Request:**
```json
{ "query": "Java developer with teamwork skills", "k": 5 }
```

**Response:**
```json
{
  "query": "Java developer with teamwork skills",
  "recommendations": [
    { "assessment_name": "...", "url": "...", "score": 0.123 }
  ]
}
```

---

## Balanced Recommendations (Requirement)

When a query spans **technical + behavioral** domains, the system enforces a **balanced mix** of:
- **K (Knowledge & Skills)** assessments
- **P (Personality & Behavior)** assessments

This logic is implemented in `api/rerank.py` and uses `test_type` from `data/normalized_products.json`.

---

## Evaluation & CSV Submission

Train labels are located at:
```
data/train_labels.csv
```

Submission format (2 columns: `Query`, `Assessment_url`):

```
Query,Assessment_url
Query 1,Recommendation 1 (URL)
Query 1,Recommendation 2 (URL)
...
Query 2,Recommendation 1 (URL)
```

---

## Deployment

### Render (recommended)
- Runtime installs **lightweight** deps from `requirements.prod.txt`
- `render.yaml` uses:
```
gunicorn api.server:app --bind 0.0.0.0:$PORT
```

### Docker (optional)
```bash
docker build -t shl-assessment .
docker run -e PORT=8181 -p 8181:8181 shl-assessment
```

---

## Notes
- Crawler is rate‑limited by default. Use `--delay` to tune.
- Ensure crawling complies with SHL’s robots.txt and usage policies.
- For production, set `HF_TOKEN` to avoid HuggingFace rate limits.
