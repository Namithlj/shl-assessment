#!/usr/bin/env python3
"""Evaluate recommendations using Mean Recall@K.

Input: labeled CSV with columns `Query` and `Assessment_url` (multiple rows per query)
Uses local retrieval (api.server) to get top-K predictions for each query.
"""
import argparse
import csv
from collections import defaultdict
from statistics import mean

from api import server


def load_labels(path):
    q2labels = defaultdict(set)
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter='\t' if '\t' in f.read(1024) else ',')
        f.seek(0)
        for row in r:
            q = row.get('Query') or row.get('query')
            url = row.get('Assessment_url') or row.get('Assessment_url')
            if q and url:
                q2labels[q.strip()].add(url.strip())
    return q2labels


def recommend_local(query, k=10):
    app = server.app
    client = app.test_client()
    r = client.post('/recommend', json={'query': query, 'k': k})
    if r.status_code != 200:
        return []
    body = r.get_json()
    return [x['url'] for x in body.get('recommendations', [])]


def recall_at_k(preds, labels):
    if not labels:
        return 0.0
    return len([p for p in preds if p in labels]) / len(labels)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('labels_csv')
    p.add_argument('--k', type=int, default=10)
    args = p.parse_args()

    q2labels = load_labels(args.labels_csv)
    recalls = []
    for q, labels in q2labels.items():
        preds = recommend_local(q, k=args.k)
        r = recall_at_k(preds, labels)
        recalls.append(r)
        print(f"Query: {q[:80]}... Recall@{args.k}: {r:.3f} (labels={len(labels)})")

    print("Mean Recall@{k}:", mean(recalls) if recalls else 0.0)


if __name__ == '__main__':
    main()
