# -*- coding: utf-8 -*-
"""
랭킹: 마감(50%) + 키워드(30%) + 출처신뢰(20%)
- close_date가 없으면 마감 점수는 0 처리
- 정렬: 마감 임박(오름) → 점수(내림) → 신뢰(내림)
"""
from typing import List, Dict
from datetime import date, datetime
import re

WEIGHTS = {"deadline": 0.5, "keyword": 0.3, "trust": 0.2}
TRUST = {"nipa": 1.0, "bizinfo": 0.9, "web": 0.6}

def _days_until(dstr: str) -> int:
    if not dstr:
        return 9999
    try:
        d = datetime.strptime(dstr, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 9999

def _deadline_score(close_date: str) -> float:
    days = _days_until(close_date)
    if days <= 0:
        return 1.0
    if days >= 30:
        return 0.0
    return max(0.0, 1.0 - (days / 30.0))

def _keyword_score(query: str, title: str, snippet: str) -> float:
    toks = re.findall(r"[가-힣A-Za-z0-9]+", query.lower())
    if not toks:
        return 0.0
    t = (title or "").lower()
    s = (snippet or "").lower()
    hit = 0.0
    for tok in toks:
        if tok in t:
            hit += 2.0
        elif tok in s:
            hit += 1.0
    denom = max(1.0, 2.0 * len(toks))
    return min(1.0, hit / denom)

def _trust_score(source: str) -> float:
    return TRUST.get(source.lower(), 0.5)

def score_item(it: Dict, query: str) -> float:
    sd = _deadline_score(it.get("close_date",""))
    sk = _keyword_score(query, it.get("title",""), it.get("snippet",""))
    st = _trust_score(it.get("source",""))
    return WEIGHTS["deadline"]*sd + WEIGHTS["keyword"]*sk + WEIGHTS["trust"]*st

def rank_items(items: List[Dict], query: str) -> List[Dict]:
    scored = []
    for it in items:
        sc = score_item(it, query)
        it2 = dict(it); it2["score"] = round(sc, 4)
        scored.append(it2)

    def sort_key(x):
        # close_date 없으면 맨 뒤
        return (_days_until(x.get("close_date","")), -x["score"], -_trust_score(x.get("source","")))
    scored.sort(key=sort_key)
    return scored
