import re
from collections import Counter


TECH_KEYWORDS = [
    "java", "python", "sql", "javascript", "react", "angular", "html", "css",
    "selenium", "automation", "excel", "tableau", "r", "spq", "opq", "c++",
]

BEHAVIORAL_KEYWORDS = [
    "collaborate", "collaboration", "team", "teamwork", "stakeholder",
    "stakeholders", "communication", "interpersonal", "behavior", "behaviour",
    "personality", "leadership", "motivation", "empathy", "conflict",
]


def extract_keywords(text):
    text = (text or "").lower()
    words = re.findall(r"[a-zA-Z+#]+", text)
    return Counter(words)


def score_by_keyword(match_keywords, meta_item):
    title = (meta_item.get("title") or "").lower()
    cat = (meta_item.get("category") or "").lower()
    score = 0.0
    for kw in match_keywords:
        if kw in title:
            score += 1.0
        if kw in cat:
            score += 0.5
    return score


def _get_meta(meta, idx):
    if isinstance(meta, dict):
        return meta.get(str(int(idx))) or meta.get(int(idx))
    if isinstance(meta, list):
        i = int(idx)
        if 0 <= i < len(meta):
            return meta[i]
    return None


def _is_individual(meta_item):
    if not meta_item:
        return False
    if "is_individual" not in meta_item:
        return True
    return bool(meta_item.get("is_individual"))


def _is_mixed_domain(query_text):
    text = (query_text or "").lower()
    has_tech = any(k in text for k in TECH_KEYWORDS)
    has_beh = any(k in text for k in BEHAVIORAL_KEYWORDS)
    return has_tech and has_beh


def _bucket_by_type(candidates, meta):
    buckets = {"K": [], "P": [], "other": []}
    for c in candidates:
        m = _get_meta(meta, c["id"])
        if not _is_individual(m):
            continue
        test_type = (m.get("test_type") or "").strip().upper()
        if test_type == "K":
            buckets["K"].append(c)
        elif test_type == "P":
            buckets["P"].append(c)
        else:
            buckets["other"].append(c)
    return buckets


def balance_results(candidates, meta, desired_k=5, require_balance=False):
    # candidates: list of dicts {'id':int, 'score':float}
    # meta: metadata dict or list
    buckets = _bucket_by_type(candidates, meta)
    tech = buckets["K"]
    beh = buckets["P"]
    other = buckets["other"]

    results = []
    if require_balance:
        # ensure at least one K and one P when available
        if tech:
            results.append(tech.pop(0))
        if beh and len(results) < desired_k:
            results.append(beh.pop(0))

    # then alternate K/P with remainder
    while len(results) < desired_k and (tech or beh or other):
        if tech:
            results.append(tech.pop(0))
        if len(results) >= desired_k:
            break
        if beh:
            results.append(beh.pop(0))
        if len(results) >= desired_k:
            break
        if other:
            results.append(other.pop(0))

    return results[:desired_k]


def rerank(query_text, candidates, meta):
    # candidates: list of {'id':int, 'score':float, 'title':..., 'url':...}
    kw_counts = extract_keywords(query_text)
    # match tech keywords
    match_keys = [k for k in kw_counts.keys() if k in TECH_KEYWORDS]

    # compute adjusted score
    adjusted = []
    for c in candidates:
        base = c.get('score', 0.0)
        m = _get_meta(meta, c['id'])
        if not _is_individual(m):
            continue
        bonus = score_by_keyword(match_keys, m) * 0.1
        adjusted.append({'id': c['id'], 'score': base + bonus, 'title': m.get('title'), 'url': m.get('url'), 'test_type': m.get('test_type')})

    adjusted = sorted(adjusted, key=lambda x: x['score'], reverse=True)
    balanced = balance_results(adjusted, meta, desired_k=len(adjusted), require_balance=_is_mixed_domain(query_text))
    return balanced
