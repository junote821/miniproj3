# -*- coding: utf-8 -*-
"""
Day3 파이프라인 진입점
- fetch → normalize → rank → 표준 JSON
"""
from typing import Dict, Any, List
from .fetchers import fetch_all
from .normalize import normalize_all
from .rank import rank_items
from sub_agents.common.schemas import GovNotices, GovNoticeItem

def find_notices(query: str) -> dict:
    raw = fetch_all(query)
    norm = normalize_all(raw)              # dict 리스트 (필드 기본 채움)
    ranked = rank_items(norm, query)       # score 채움/정렬
    model = GovNotices(
        query=query,
        items=[GovNoticeItem(**it) for it in ranked]
    )
    return model.model_dump()