from flask import Flask, request, jsonify, send_from_directory
import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import joblib
from .rerank import rerank

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_DIR = os.path.normpath(DATA_DIR)

app = Flask(__name__)


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
    model = SentenceTransformer(model_name)
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
            return jsonify({"error": str(e)}), 500

    vec = model.encode([q])[0]
    dists, ids = nn.kneighbors([vec], n_neighbors=min(max(10, k*2), embs.shape[0]))
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
