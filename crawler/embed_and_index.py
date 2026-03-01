#!/usr/bin/env python3
"""Generate embeddings for normalized products and build an Annoy index.

Outputs:
- data/embeddings.npy (optional)
- data/annoy_index.ann
- data/metadata.json
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
import joblib


def load_products(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_embeddings(products, model_name="all-MiniLM-L6-v2", out_dir="data"):
    model = SentenceTransformer(model_name)
    texts = []
    for p in products:
        parts = [p.get("title", ""), p.get("category", ""), p.get("test_type", "")]
        texts.append(" | ".join([t for t in parts if t]))

    embs = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    os.makedirs(out_dir, exist_ok=True)
    emb_path = os.path.join(out_dir, "embeddings.npy")
    np.save(emb_path, embs)

    # Build brute-force NearestNeighbors with cosine distance
    nn = NearestNeighbors(n_neighbors=10, metric="cosine", algorithm="brute")
    nn.fit(embs)
    idx_path = os.path.join(out_dir, "nn_model.joblib")
    joblib.dump(nn, idx_path)

    # Save metadata
    meta = {i: {"title": p.get("title"), "url": p.get("url"), "duration_minutes": p.get("duration_minutes"), "category": p.get("category") } for i, p in enumerate(products)}
    with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved embeddings to {emb_path}, NearestNeighbors model to {idx_path}, metadata to {out_dir}/metadata.json")
    return emb_path, idx_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inpath", default="data/normalized_products.json")
    p.add_argument("--out", dest="outdir", default="data")
    p.add_argument("--model", default="all-MiniLM-L6-v2")
    args = p.parse_args()
    products = load_products(args.inpath)
    build_embeddings(products, model_name=args.model, out_dir=args.outdir)


if __name__ == "__main__":
    main()
