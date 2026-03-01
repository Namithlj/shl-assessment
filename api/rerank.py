import re
from collections import Counter


TECH_KEYWORDS = [
    "java", "python", "sql", "javascript", "react", "angular", "html", "css",
    "selenium", "automation", "excel", "tableau", "r", "spq", "opq", "c++",
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


def balance_results(candidates, meta, desired_k=5):
    # candidates: list of dicts {'id':int, 'score':float}
    # meta: metadata dict
    # Ensure a simple balance: prefer mix of items whose category contains 'personality' / 'behaviour' vs 'knowledge' / 'skills'
    behavioural = []
    technical = []
    other = []
    for c in candidates:
        m = meta.get(str(c['id'])) or meta.get(c['id'])
        cat = (m.get('category') or "").lower()
        title = (m.get('title') or "").lower()
        if 'person' in cat or 'behaviour' in title or 'interpersonal' in title or 'personality' in title:
            behavioural.append(c)
        elif any(tk in title for tk in TECH_KEYWORDS) or any(tk in cat for tk in TECH_KEYWORDS):
            technical.append(c)
        else:
            other.append(c)

    results = []
    # alternate technical and behavioural when possible
    while len(results) < desired_k and (technical or behavioural or other):
        if technical:
            results.append(technical.pop(0))
        if len(results) >= desired_k:
            break
        if behavioural:
            results.append(behavioural.pop(0))
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
        m = meta.get(str(c['id'])) or meta.get(c['id'])
        bonus = score_by_keyword(match_keys, m) * 0.1
        adjusted.append({'id': c['id'], 'score': base + bonus, 'title': m.get('title'), 'url': m.get('url')})

    adjusted = sorted(adjusted, key=lambda x: x['score'], reverse=True)
    balanced = balance_results(adjusted, meta, desired_k=len(adjusted))
    return balanced
