from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
import json
import numpy as np
try:
    # optional import; heavy dependency avoided in prod requirements
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None
import joblib
from .rerank import rerank

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.normpath(DATA_DIR)

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_resources(model_name="all-MiniLM-L6-v2"):
    meta_path = os.path.join(DATA_DIR, "metadata.json")
    nn_path = os.path.join(DATA_DIR, "nn_model.joblib")
    emb_path = os.path.join(DATA_DIR, "embeddings.npy")
    if not os.path.exists(meta_path) or not os.path.exists(nn_path) or not os.path.exists(emb_path):
        raise RuntimeError("Required data (metadata/nn_model/embeddings) not found in data/")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    nn = joblib.load(nn_path)
    embs = np.load(emb_path)
    model = None
    if SentenceTransformer is not None:
        try:
            model = SentenceTransformer(model_name)
        except Exception:
            model = None
    else:
        logger = logging.getLogger(__name__)
        logger.warning("SentenceTransformer not installed; runtime encoding disabled")
    return meta, nn, embs, model


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/recommend", methods=["POST"])
def recommend():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "invalid json"}), 400
    q = payload.get("query") or payload.get("text") or payload.get("job_description")
    if not q:
        return jsonify({"error": "missing 'query' field"}), 400
    k = int(payload.get("k", 5))
    try:
        meta, nn, embs, model = app.config.get("RESOURCES")
    except Exception:
        try:
            meta, nn, embs, model = load_resources()
            app.config["RESOURCES"] = (meta, nn, embs, model)
        except Exception as e:
            logger.exception("Failed to load resources")
            return jsonify({"error": "loading resources failed", "detail": str(e)}), 500

    try:
        if model is not None:
            vec = model.encode([q])[0]
        else:
            # fall back to OpenAI embeddings if available
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                import requests
                resp = requests.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={"input": q, "model": "text-embedding-3-small"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    return jsonify({"error": "embedding failed", "detail": resp.text}), 502
                vec = resp.json()["data"][0]["embedding"]
            else:
                return jsonify({"error": "encoding unavailable", "detail": "server not configured with sentence-transformers and OPENAI_API_KEY is missing"}), 503
        dists, ids = nn.kneighbors([vec], n_neighbors=min(max(10, k*2), embs.shape[0]))
    except Exception as e:
        logger.exception("Vector search failed")
        return jsonify({"error": "vector search failed", "detail": str(e)}), 500
    candidates = []
    for dist, i in zip(dists[0], ids[0]):
        candidates.append({"id": int(i), "score": float(1 - float(dist))})

    # rerank and balance
    final = rerank(q, candidates, meta)
    recs = []
    for item in final[:k]:
        recs.append({
            "assessment_name": item.get("title"),
            "url": item.get("url"),
            "score": item.get("score")
        })

    return jsonify({"query": q, "recommendations": recs}), 200


@app.route('/recommend', methods=['GET'])
def recommend_get():
    # Debug GET endpoint to help identify 404s from simple browser checks.
    q = request.args.get('q') or request.args.get('query')
    if not q:
        return jsonify({"error": "provide ?q=<text> to test GET recommendation"}), 400
    try:
        meta, nn, embs, model = app.config.get("RESOURCES")
    except Exception:
        try:
            meta, nn, embs, model = load_resources()
            app.config["RESOURCES"] = (meta, nn, embs, model)
        except Exception as e:
            logger.exception("Failed to load resources for GET recommend")
            return jsonify({"error": "loading resources failed", "detail": str(e)}), 500

    try:
            if model is not None:
                vec = model.encode([q])[0]
            else:
                openai_key = os.environ.get("OPENAI_API_KEY")
                if openai_key:
                    import requests
                    resp = requests.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                        json={"input": q, "model": "text-embedding-3-small"},
                        timeout=10,
                    )
                    if resp.status_code != 200:
                        return jsonify({"error": "embedding failed", "detail": resp.text}), 502
                    vec = resp.json()["data"][0]["embedding"]
                else:
                    return jsonify({"error": "encoding unavailable (GET)", "detail": "server not configured with sentence-transformers and OPENAI_API_KEY is missing"}), 503
            dists, ids = nn.kneighbors([vec], n_neighbors=min(10, embs.shape[0]))
    except Exception as e:
        logger.exception("Vector search failed (GET)")
        return jsonify({"error": "vector search failed", "detail": str(e)}), 500

    out = []
    for dist, i in zip(dists[0], ids[0]):
        # metadata can be a dict (string keys) or a list; handle both safely
        m = None
        try:
            if isinstance(meta, dict):
                # try string key first, then int key
                m = meta.get(str(int(i))) or meta.get(int(i))
            elif isinstance(meta, list):
                idx = int(i)
                if 0 <= idx < len(meta):
                    m = meta[idx]
        except Exception:
            m = None
        if not m:
            logger.warning('Missing metadata for id %s; skipping', i)
            continue
        out.append({"title": m.get('title'), "url": m.get('url'), "score": float(1 - float(dist))})
    return jsonify({"query": q, "candidates": out}), 200


if __name__ == "__main__":
    # preload resources
    try:
        app.config["RESOURCES"] = load_resources()
    except Exception as e:
        print("Warning: resources not loaded:", e)
    app.run(host="127.0.0.1", port=8181, debug=True)


@app.route("/", methods=["GET"])
def index():
    # serve frontend index if present
    frontend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(frontend_dir, "index.html")
    return jsonify({"message": "SHL Recommender API"}), 200


@app.route('/<path:filename>', methods=['GET'])
def frontend_files(filename):
    # Serve other frontend static assets (css/js) if present in frontend/ directory
    frontend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    file_path = os.path.join(frontend_dir, filename)
    if os.path.exists(file_path):
        return send_from_directory(frontend_dir, filename)
    # If not a static file, return 404 so API routes can handle other paths
    return jsonify({"error": "not found"}), 404
