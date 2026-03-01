#!/usr/bin/env python3
"""Generate submission CSV from test queries using local recommender.

Input: CSV with header `Query` (one row per query)
Output: CSV with columns `Query` and `Assessment_url` repeating rows per recommendation.
"""
import argparse
import csv
from api import server


def recommend_local(query, k=10):
    app = server.app
    client = app.test_client()
    r = client.post('/recommend', json={'query': query, 'k': k})
    if r.status_code != 200:
        return []
    body = r.get_json()
    return [x['url'] for x in body.get('recommendations', [])]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('test_csv')
    p.add_argument('out_csv')
    p.add_argument('--k', type=int, default=10)
    args = p.parse_args()

    queries = []
    with open(args.test_csv, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            q = row.get('Query') or row.get('query')
            if q:
                queries.append(q.strip())

    with open(args.out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Query', 'Assessment_url'])
        for q in queries:
            preds = recommend_local(q, k=args.k)
            for url in preds:
                w.writerow([q, url])

    print(f'Wrote predictions to {args.out_csv}')


if __name__ == '__main__':
    main()
