# SHL Assessment Catalog Crawler

This small project contains a crawler to download the SHL product catalogue pages and extract individual assessment pages (title, URL, category, duration, test type).

Quick start (Windows PowerShell):

1. Create a virtualenv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the crawler (saves to `data/products.json` and `data/products.csv`):

```powershell
python crawler\scrape_shl.py --out data/products.json
```

Run the API + Frontend (local):

```powershell
# activate venv if needed
c:/python313/python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# start the Flask API (serves frontend at /)
python -m api.server

# open http://127.0.0.1:8181/ in your browser to use the demo frontend
```

Notes:
- The script is polite (rate-limited). If you need to crawl faster, adjust `--delay`.
- You must ensure crawling the target site complies with their robots.txt and your legal/organizational rules.

Deploying to Render / Heroku
 - Ensure `requirements.txt` includes `gunicorn` (already present).
 - Add the project `Procfile` (already added) which tells the host to run:
	 `gunicorn api.server:app --bind 0.0.0.0:$PORT`.
 - On Render or Heroku create a new Web Service, connect the GitHub repo, and deploy. Check the service logs if you see a "Not Found" page — it usually means the deploy target URL is wrong or the service failed to start.

If you want a Docker deployment instead I can add a `Dockerfile` and a `render.yaml` for a full Render setup.
