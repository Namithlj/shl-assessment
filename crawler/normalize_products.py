#!/usr/bin/env python3
"""Normalize scraped SHL product data and filter individual test solutions.

Outputs: data/normalized_products.json and data/normalized_products.csv
"""
import argparse
import json
import os
import re
from urllib.parse import urlparse

import pandas as pd


def load_input(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_duration(text):
    if not text:
        return None
    m = re.search(r"(\d{1,3})", text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def is_individual_solution(item):
    # Heuristics: exclude listings that mention 'Pre-packaged' or 'Solution' in category/title
    title = (item.get("title") or "").lower()
    cat = (item.get("category") or "").lower()
    url = item.get("url") or ""
    if "pre-packag" in title or "pre-packag" in cat:
        return False
    # Many product pages for collections include 'solution' or 'pack' in URL or title
    if "/products/product-catalog/view/" in url or "/solutions/products/product-catalog/view/" in url:
        # still filter out if title contains 'solution' and likely a multi-test package
        if "pre-packag" in title or "solution" in title and "entry" not in title:
            return False
        return True
    return False


def normalize(items):
    rows = []
    for it in items:
        title = (it.get("title") or "").strip()
        url = it.get("url") or ""
        category = (it.get("category") or "").strip()
        duration = parse_duration(it.get("duration") or "")
        test_type = (it.get("test_type") or "").strip()
        individual = is_individual_solution(it)
        parsed = urlparse(url)
        slug = os.path.basename(parsed.path)
        rows.append({
            "title": title,
            "url": url,
            "slug": slug,
            "category": category,
            "duration_minutes": duration,
            "test_type": test_type,
            "is_individual": individual,
        })
    return rows


def save(rows, out_prefix):
    os.makedirs(os.path.dirname(out_prefix), exist_ok=True)
    json_path = out_prefix + ".json"
    csv_path = out_prefix + ".csv"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return json_path, csv_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inpath", default="data/products.json")
    p.add_argument("--out", dest="outprefix", default="data/normalized_products")
    args = p.parse_args()
    items = load_input(args.inpath)
    rows = normalize(items)
    json_path, csv_path = save(rows, args.outprefix)
    df = pd.DataFrame(rows)
    total = len(df)
    individual = df["is_individual"].sum()
    print(f"Total records: {total}")
    print(f"Individual test solutions (heuristic): {individual}")
    print(f"Saved: {json_path} and {csv_path}")


if __name__ == "__main__":
    main()
