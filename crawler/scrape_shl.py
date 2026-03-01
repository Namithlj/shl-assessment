#!/usr/bin/env python3
"""Simple SHL product catalog crawler.

Saves structured product data to JSON and CSV.
"""
import argparse
import json
import os
import re
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


def fetch(url, session, timeout=15):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def extract_product_links(html):
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.select("a[href]"):
        href = a["href"]
        if re.search(r"/products/product-catalog/view/", href) or re.search(r"/solutions/products/product-catalog/view/", href):
            full = urljoin(BASE, href)
            links.add(full)
    return links


def parse_product_page(html, url):
    soup = BeautifulSoup(html, "lxml")
    # title heuristics
    title_tag = soup.find(["h1", "h2"]) or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # try to find metadata fields like Duration, Test Type
    text = soup.get_text(separator="\n")
    duration = ""
    test_type = ""

    # Duration patterns (e.g., 'Duration: 40 minutes')
    m = re.search(r"Duration[:\s]+([0-9]{1,3}\s*(minutes|mins|min))", text, re.IGNORECASE)
    if m:
        duration = m.group(1)

    # Test Type / Test category
    m2 = re.search(r"Test Type[:\s]*([A-Za-z &-]+)", text, re.IGNORECASE)
    if m2:
        test_type = m2.group(1).strip()

    # Breadcrumb/category
    category = ""
    bc = soup.select("nav.breadcrumb, .breadcrumb")
    if bc:
        category = bc[0].get_text(" > ", strip=True)

    return {
        "title": title,
        "url": url,
        "category": category,
        "duration": duration,
        "test_type": test_type,
    }


def crawl(out_path, delay=1.0, max_products=None):
    session = requests.Session()
    session.headers.update({"User-Agent": "shl-crawler/0.1 (+https://example.com)"})

    print(f"Fetching catalog: {CATALOG_URL}")
    cat_html = fetch(CATALOG_URL, session)
    product_links = extract_product_links(cat_html)

    # also try to follow pagination or category links on catalog page
    soup = BeautifulSoup(cat_html, "lxml")
    for a in soup.select("a[href]"):
        href = a["href"]
        if "/product-catalog/page/" in href or "product-catalog?" in href:
            try:
                page_html = fetch(urljoin(BASE, href), session)
                product_links.update(extract_product_links(page_html))
            except Exception:
                pass

    product_links = sorted(product_links)
    if max_products:
        product_links = product_links[:max_products]

    print(f"Found {len(product_links)} product links; crawling each (delay={delay}s)")
    results = []
    for url in tqdm(product_links):
        try:
            html = fetch(url, session)
            data = parse_product_page(html, url)
            results.append(data)
        except Exception as e:
            print(f"Failed {url}: {e}")
        time.sleep(delay)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # also write CSV
    df = pd.DataFrame(results)
    csv_path = os.path.splitext(out_path)[0] + ".csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(results)} products to {out_path} and {csv_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/products.json", help="output JSON path")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--max", type=int, default=None, help="max products to fetch (for testing)")
    args = p.parse_args()
    crawl(args.out, delay=args.delay, max_products=args.max)


if __name__ == "__main__":
    main()
