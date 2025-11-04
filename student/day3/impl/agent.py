# -*- coding: utf-8 -*-
"""
Day3Agent: 정부사업 공고 에이전트(Agent-as-a-Tool)
- 입력: query(str), plan(Day3Plan)
- 동작: fetch → normalize → rank
- 출력: {"type":"gov_notices","query": "...","items":[...]}  // items는 정규화된 공고 리스트
"""

from __future__ import annotations
from typing import Dict, Any
import os

from student.common.schemas import Day3Plan

# 수집 → 정규화 → 랭크 모듈
from . import fetchers          # NIPA, Bizinfo, 일반 Web 수집
from .normalize import normalize_all   # raw → 공통 스키마 변환
from .rank import rank_items           # 쿼리와의 관련도/마감일/신뢰도 등으로 정렬


def _set_source_topk(plan: Day3Plan) -> Day3Plan:
    """
    fetchers 모듈의 (기본)소스별 TopK 상수와 plan 값을 싱크.
    - 이 함수는 실습 편의를 위해 제공. 내부에서 fetchers.NIPA_TOPK 등 값 갱신.
    """
    # TODO[DAY3-I-01]:
    # 1) plan.nipa_topk, plan.bizinfo_topk, plan.web_topk 값을 정수로 변환해 1 이상으로 보정
    # 2) fetchers.NIPA_TOPK / fetchers.BIZINFO_TOPK / fetchers.WEB_TOPK에 반영
    # 3) 보정한 plan을 반환
    # ----------------------------------------------------------------------------
    # 정답 구현:
    plan.nipa_topk = max(1, int(plan.nipa_topk))
    plan.bizinfo_topk = max(1, int(plan.bizinfo_topk))
    plan.web_topk = max(0, int(plan.web_topk))  # 웹은 0도 허용

    fetchers.NIPA_TOPK = plan.nipa_topk
    fetchers.BIZINFO_TOPK = plan.bizinfo_topk
    fetchers.WEB_TOPK = plan.web_topk
    return plan


class Day3Agent:
    def __init__(self):
        """
        외부 API 키 등 환경변수 확인 (없어도 동작은 하되 결과가 빈 배열일 수 있음)
        - 예: os.getenv("TAVILY_API_KEY", "")
        """
        # TODO[DAY3-I-02]: 필요한 키를 읽고, 인스턴스 필드로 보관(옵션)
        # ----------------------------------------------------------------------------
        # 정답 구현:
        self.tavily_key = os.getenv("TAVILY_API_KEY", "")

    def handle(self, query: str, plan: Day3Plan = Day3Plan()) -> Dict[str, Any]:
        """
        End-to-End 파이프라인:
          1) _set_source_topk(plan)  // 입력 plan의 topk를 fetchers에 반영
          2) fetch 단계
             - NIPA: fetchers.fetch_nipa(query, plan.nipa_topk)
             - Bizinfo: fetchers.fetch_bizinfo(query, plan.bizinfo_topk)
             - Web fallback(옵션): plan.use_web_fallback and plan.web_topk > 0 이면 fetchers.fetch_web(...)
             → raw 리스트에 모두 누적
          3) normalize 단계: normalize_all(raw)
             - 출처가 제각각인 raw를 공통 스키마(제목/title, URL, 마감/기간, 주체/부처 등)로 변환
          4) rank 단계: rank_items(norm, query)
             - 질의 관련도, 마감 임박도, 신뢰도 점수 등을 반영해 정렬/필터링
          5) 결과 페이로드 구성:
             { "type": "gov_notices", "query": query, "items": ranked }
        예외 처리:
          - 각 단계에서 예외가 난다면 최소한 비어 있는 리스트라도 반환하도록 하거나,
            상위에서 try/except로 감싼다(이번 과제에선 간단 구현 권장).
        """
        # TODO[DAY3-I-03]: 위 단계 구현
        # ----------------------------------------------------------------------------
        # 정답 구현:
        # 1) 소스별 TopK 반영
        _set_source_topk(plan)

        # 2) Fetch 단계
        raw = []
        try:
            raw += fetchers.fetch_nipa(query, plan.nipa_topk)
        except Exception as e:
            raw += []
        try:
            raw += fetchers.fetch_bizinfo(query, plan.bizinfo_topk)
        except Exception as e:
            raw += []
        if plan.use_web_fallback and plan.web_topk > 0:
            try:
                raw += fetchers.fetch_web(query, plan.web_topk)
            except Exception as e:
                raw += []

        # 3) Normalize
        try:
            norm = normalize_all(raw)
        except Exception:
            norm = []

        # 4) Rank
        try:
            ranked = rank_items(norm, query)
        except Exception:
            ranked = norm  # 최소한 정규화된 순서 그대로라도

        # 5) Payload 반환
        return {
            "type": "gov_notices",
            "query": query,
            "items": ranked,
        }
