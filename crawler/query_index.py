#!/usr/bin/env python3
"""Query the Annoy index to retrieve top-k product recommendations for a text query."""
import argparse
import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
import joblib


def load_meta(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def query(text, topk=5, model_name="all-MiniLM-L6-v2", data_dir="data"):
    meta_path = os.path.join(data_dir, "metadata.json")
    idx_path = os.path.join(data_dir, "nn_model.joblib")
    emb_path = os.path.join(data_dir, "embeddings.npy")
    if not os.path.exists(meta_path) or not os.path.exists(idx_path):
        raise RuntimeError("Index or metadata not found. Run embed_and_index.py first.")

    meta = load_meta(meta_path)
    model = SentenceTransformer(model_name)
    vec = model.encode([text])[0]

    nn = joblib.load(idx_path)
    embs = np.load(emb_path)
    dists, ids = nn.kneighbors([vec], n_neighbors=topk)
    results = []
    for dist, i in zip(dists[0], ids[0]):
        m = meta.get(str(i)) or meta.get(i)
        # cosine distance -> similarity
        score = float(1 - dist)
        results.append({"score": score, "id": int(i), "title": m.get("title"), "url": m.get("url")})
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--q", required=True)
    p.add_argument("--k", type=int, default=5)
    args = p.parse_args()
    res = query(args.q, topk=args.k)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
