# -*- coding: utf-8 -*-
"""
Day3 - 나라장터(PPS) 공고 탐색 에이전트 (강사용/답지)
- pps_api.pps_fetch_bids 를 호출해 GovNotice 스키마로 결과를 만들고,
  표준 dict로 반환 (LLM은 메타데이터 정리용으로만 지정)
"""
from __future__ import annotations
from typing import Dict, Any

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from student.common.schemas import GovNotices, GovNoticeItem
from student.day3.impl.pps_api import pps_fetch_bids


def _handle(query: str) -> Dict[str, Any]:
    """
    1) 나라장터 OpenAPI로 질의어 검색
    2) GovNotices 스키마로 직렬화(dict)
    """
    raw_items = pps_fetch_bids(query)
    items = [GovNoticeItem(**it) for it in raw_items]
    model = GovNotices(query=query, items=items)
    return model.model_dump()


# ※ day1/day2와 동일한 패턴: handle만 가진 경량 Agent
day3_pps_agent = Agent(
    name="Day3PpsAgent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    description="조달청 나라장터 OpenAPI를 사용해 입찰/사업 공고를 조회합니다.",
    instruction=(
        "사용자의 질의를 나라장터(OpenAPI) 검색어로 사용해 공고 목록을 가져오고, "
        "GovNotices 표준 스키마(dict)로 반환하세요. LLM으로 새로운 내용을 생성하지 말고 "
        "API 응답 필드만 정리하세요."
    ),
    handle=_handle,
)
