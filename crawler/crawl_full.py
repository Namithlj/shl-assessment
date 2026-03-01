#!/usr/bin/env python3
"""Recursive SHL crawler to discover product pages across the site.

This performs a BFS starting from the product catalog and follows internal links
under /products/ and /solutions/ to find product detail pages. Outputs JSON list
of product records (title, url, raw_html).
"""
import argparse
import json
import os
import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://www.shl.com"
START = "https://www.shl.com/solutions/products/product-catalog/"


def fetch(url, session, timeout=15):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def is_internal(url):
    p = urlparse(url)
    if not p.netloc:
        return True
    return p.netloc.endswith("shl.com")


def extract_links(html, base=BASE):
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.select("a[href]"):
        href = a["href"].strip()
        if href.startswith("#"):
            continue
        full = urljoin(base, href)
        if is_internal(full):
            links.add(full)
    return links


def looks_like_product(url):
    # Heuristic: product detail pages contain '/product-catalog/view/' or '/view/' and '/product-catalog' elsewhere
    if re.search(r"/product-catalog/view/", url) or re.search(r"/products/product-catalog/view/", url) or re.search(r"/solutions/products/product-catalog/view/", url):
        return True
    # also include pages under /products/product-catalog/ or /solutions/products/product-catalog/ that end with a slug
    return False


def parse_title(html):
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find(["h1", "h2"]) or soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def crawl(out_path, delay=0.3, max_products=500, max_pages=2000):
    session = requests.Session()
    session.headers.update({"User-Agent": "shl-crawler/0.2 (+https://example.com)"})

    queue = deque([START])
    seen = set()
    product_urls = set()
    pages_crawled = 0
    results = []

    pbar = tqdm(total=max_pages)
    while queue and pages_crawled < max_pages and len(product_urls) < max_products:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch(url, session)
        except Exception:
            continue
        pages_crawled += 1
        pbar.update(1)

        # extract product links
        for link in extract_links(html):
            if link in seen:
                continue
            # if looks like product, add to product set
            if looks_like_product(link):
                product_urls.add(link)
            # otherwise, queue category/catalog pages under /products or /solutions
            parsed = urlparse(link)
            if parsed.path.startswith("/products") or parsed.path.startswith("/solutions") or parsed.path.startswith("/solutions/products"):
                queue.append(link)

        # small sleep to be polite
        time.sleep(delay)

    pbar.close()

    # fetch each product page and extract title
    for url in tqdm(sorted(product_urls), desc="fetch products"):
        try:
            html = fetch(url, session)
            title = parse_title(html)
            results.append({"title": title, "url": url, "html": html})
        except Exception:
            continue
        time.sleep(delay)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Discovered {len(results)} product pages. Saved to {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/products_full.json")
    p.add_argument("--delay", type=float, default=0.3)
    p.add_argument("--max_products", type=int, default=500)
    p.add_argument("--max_pages", type=int, default=2000)
    args = p.parse_args()
    crawl(args.out, delay=args.delay, max_products=args.max_products, max_pages=args.max_pages)


if __name__ == "__main__":
    main()
