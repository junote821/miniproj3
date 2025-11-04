# -*- coding: utf-8 -*-
"""
Day1 본체
- 역할: 웹 검색 / 주가 / 기업개요(추출+요약)를 병렬로 수행하고 결과를 정규 스키마로 병합
"""

from __future__ import annotations
from dataclasses import asdict
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.adk.models.lite_llm import LiteLlm
from sub_agents.common.schemas import Day1Plan
from sub_agents.day1.impl.merge import merge_day1_payload
# 외부 I/O
from sub_agents.day1.impl.tavily_client import search_tavily, extract_url
from sub_agents.day1.impl.finance_client import get_quotes
from sub_agents.day1.impl.web_search import (
    looks_like_ticker,
    search_company_profile,
    extract_and_summarize_profile,
)

DEFAULT_WEB_TOPK = 6
MAX_WORKERS = 4
DEFAULT_TIMEOUT = 20

# ------------------------------------------------------------------------------
# TODO[DAY1-I-01] 요약용 경량 LLM 준비
#  - 목적: 기업 개요 본문을 Extract 후 간결 요약
#  - LiteLlm(model="openai/gpt-4o-mini") 형태로 _SUM에 할당
# ------------------------------------------------------------------------------
# 정답 구현:
_SUM: Optional[LiteLlm] = LiteLlm(model="openai/gpt-4o-mini")


def _summarize(text: str) -> str:
    """
    입력 텍스트를 LLM으로 3~5문장 수준으로 요약합니다.
    실패 시 빈 문자열("")을 반환해 상위 로직이 안전하게 진행되도록 합니다.
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-I-02] 구현 지침
    #  - _SUM이 None이면 "" 반환(요약 생략)
    #  - _SUM.invoke({...}) 혹은 단순 텍스트 인자 형태로 호출 가능한 래퍼라면
    #    응답 객체에서 본문 텍스트를 추출하여 반환
    #  - 예외 발생 시 빈 문자열 반환
    # ----------------------------------------------------------------------------
    # 정답 구현:
    if _SUM is None:
        return ""
    try:
        resp = _SUM.invoke(text)
        # google.adk LiteLlm 응답 형태: resp.content.parts[0].text (동일 패턴 유지)
        return getattr(resp.content.parts[0], "text", "") or ""
    except Exception:
        return ""


class Day1Agent:
    def __init__(self, tavily_api_key: Optional[str], web_topk: int = DEFAULT_WEB_TOPK, request_timeout: int = DEFAULT_TIMEOUT):
        """
        필드 저장만 담당합니다.
        - tavily_api_key: Tavily API 키(없으면 웹 호출 실패 가능)
        - web_topk: 기본 검색 결과 수
        - request_timeout: 각 HTTP 호출 타임아웃(초)
        """
        # ----------------------------------------------------------------------------
        # TODO[DAY1-I-03] 필드 저장
        #  self.tavily_api_key = tavily_api_key
        #  self.web_topk = web_topk
        #  self.request_timeout = request_timeout
        # ----------------------------------------------------------------------------
        # 정답 구현:
        self.tavily_api_key = tavily_api_key
        self.web_topk = web_topk
        self.request_timeout = request_timeout

    def handle(self, query: str, plan: Day1Plan) -> Dict[str, Any]:
        """
        병렬 파이프라인:
          1) results 스켈레톤 만들기
             results = {"type":"web_results","query":query,"analysis":asdict(plan),"items":[],
                        "tickers":[], "errors":[], "company_profile":"", "profile_sources":[]}
          2) ThreadPoolExecutor(max_workers=MAX_WORKERS)에서 작업 제출:
             - plan.do_web: search_tavily(검색어, 키, top_k=self.web_topk, timeout=...)
             - plan.do_stocks: get_quotes(plan.tickers)
             - (기업개요) looks_like_ticker(query) 또는 plan에 tickers가 있을 때:
                 · search_company_profile(query, api_key, topk=2) → URL 상위 1~2개
                 · extract_and_summarize_profile(urls, api_key, summarizer=_summarize)
          3) as_completed로 결과 수집. 실패 시 results["errors"]에 '작업명:에러' 저장.
          4) merge_day1_payload(results) 호출해 최종 표준 스키마 dict 반환.
        """
        # ----------------------------------------------------------------------------
        # TODO[DAY1-I-04] 구현 지침(권장 구조)
        #  - results 초기화 (위 키 포함)
        #  - futures 딕셔너리: future -> "web"/"stock"/"profile" 등 라벨링
        #  - 병렬 제출 조건 체크(plan.do_web, plan.do_stocks, 기업개요 조건)
        #  - 완료 수집:
        #      kind == "web"    → results["items"] = data
        #      kind == "stock"  → results["tickers"] = data
        #      kind == "profile"→ results["company_profile"] = text; results["profile_sources"] = urls(옵션)
        #  - 예외: results["errors"].append(f"{kind}: {type(e).__name__}: {e}")
        #  - return merge_day1_payload(results)
        # ----------------------------------------------------------------------------
        # 정답 구현:
        results: Dict[str, Any] = {
            "type": "web_results",
            "query": query,
            "analysis": asdict(plan),
            "items": [],
            "tickers": [],
            "errors": [],
            "company_profile": "",
            "profile_sources": [],
        }

        futures = {}
        def submit_profile_job(q: str):
            # 검색 → 상위 URL 정제 → 추출/요약까지 한 번에 처리
            def job() -> Tuple[str, List[str]]:
                search_res = search_company_profile(q, self.tavily_api_key, topk=2, timeout=self.request_timeout)
                urls = [extract_url(r.get("url")) for r in (search_res or []) if r.get("url")]
                urls = [u for u in urls if u][:2]
                if not urls:
                    return "", []
                summary = extract_and_summarize_profile(urls, self.tavily_api_key, summarizer=_summarize)
                return summary or "", urls
            return job

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            # 웹 검색
            if plan.do_web:
                q = " ".join(plan.web_keywords) if plan.web_keywords else query
                futures[ex.submit(search_tavily, q, self.tavily_api_key, self.web_topk, self.request_timeout)] = "web"
            # 주가
            if plan.do_stocks and plan.tickers:
                futures[ex.submit(get_quotes, plan.tickers, self.request_timeout)] = "stock"
            # 기업개요: 질의가 티커처럼 보이거나, 계획에 티커가 있는 경우 시도
            if looks_like_ticker(query) or (plan.tickers and len(plan.tickers) > 0) or ("기업" in query or "회사" in query or "profile" in query.lower()):
                futures[ex.submit(submit_profile_job(query))] = "profile"

            for fut in as_completed(futures):
                kind = futures[fut]
                try:
                    data = fut.result(timeout=self.request_timeout)
                    if kind == "web":
                        # search_tavily 표준 반환(list[dict]) 가정
                        results["items"] = data or []
                    elif kind == "stock":
                        # get_quotes 표준 반환(list[dict]) 가정
                        results["tickers"] = data or []
                    elif kind == "profile":
                        # (summary, urls)
                        summary, urls = data if isinstance(data, tuple) else ("", [])
                        if summary:
                            results["company_profile"] = summary
                        if urls:
                            results["profile_sources"] = urls[:2]
                except Exception as e:
                    results["errors"].append(f"{kind}: {type(e).__name__}: {e}")

        # 표준 스키마로 병합
        return merge_day1_payload(results)
