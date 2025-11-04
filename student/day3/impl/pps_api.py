# -*- coding: utf-8 -*-
"""
나라장터(PPS) Open API 클라이언트
- data.go.kr의 조달청 입찰공고 API를 호출해 공고 목록을 수집
- 엔드포인트/파라미터명을 .env로 설정 가능하게 만들어, API 스펙 변동에도 유연하게 대응

필수 .env (예시)
PPS_SERVICE_KEY=...              # 발급받은 디코딩 전 키(그대로 사용)
PPS_BASE_URL=https://apis.data.go.kr
PPS_ENDPOINT=/1230000/BidPublicInfoService02/getBidPblancListInfoCnstwk
PPS_QUERY_PARAM=bidNtceNm        # 검색어 파라미터명(스펙에 따라 다를 수 있음, 기본값: bidNtceNm)
PPS_DATE_FROM=202501010000       # 공고조회 시작일(YYYYMMDDHHMM 또는 API에 맞는 포맷)
PPS_DATE_TO=202512312359         # 공고조회 종료일
PPS_ROWS=100                     # 페이지당 건수
PPS_PAGE_MAX=3                   # 최대 페이지 수
PPS_INQRY_DIV=1                  # 조회구분(스펙별 사용; 없으면 자동 제외)
"""

from __future__ import annotations
import os, re
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import requests
from datetime import datetime

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": os.getenv("USER_AGENT", "KT-AIVLE/Day3PPSAgent")})

# 날짜 파싱 보조
def _to_iso_date(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # 흔한 포맷 시도: YYYYMMDDHHMM, YYYYMMDD, YYYY-MM-DD HH:MM, ...
    for fmt in ("%Y%m%d%H%M", "%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    # 숫자만 8자리면 YYYYMMDD로 시도
    if s.isdigit() and len(s) == 8:
        try:
            return datetime.strptime(s, "%Y%m%d").date().isoformat()
        except Exception:
            pass
    return ""

def _get_env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v if v is not None else default

def _build_url(base: str, endpoint: str, params: Dict[str, Any]) -> str:
    if base.endswith("/"):
        base = base[:-1]
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return f"{base}{endpoint}?{urlencode(params, doseq=True, safe=':/')}"

def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    data.go.kr 조달청 API 표준 형태를 가정:
    { "response": { "body": { "items": { "item": [ {...}, ... ] }}}}
    일부 응답은 item이 dict 단일일 수 있으므로 리스트화 처리
    """
    try:
        resp = payload.get("response", {})
        body = resp.get("body", {})
        items = body.get("items", {})
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return item
    except Exception:
        pass
    return []

def _to_notice(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    GovNotice 스키마로 매핑
    - title: bidNtceNm
    - url: bidNtceDtlUrl (없으면 공고번호로 상세 URL 조합은 보류)
    - agency: ntceInsttNm
    - announce_date: ntceDt
    - close_date: bidClseDt or opengDt
    - budget: presmptPrce/asignBdgtAmt 중 첫 발견값
    """
    title = str(item.get("bidNtceNm", "")).strip()
    url = str(item.get("bidNtceDtlUrl", "")).strip()
    agency = str(item.get("ntceInsttNm", "")).strip()

    # 날짜들: 스펙에 따라 필드명이 다를 수 있어 후보 리스트 순회
    announce = _to_iso_date(str(item.get("ntceDt", "")).strip())
    close = ""
    for key in ("bidClseDt", "opengDt", "rlOpngDt", "bidEndDt"):
        val = str(item.get(key, "")).strip()
        if val:
            close = _to_iso_date(val)
            if close:
                break

    budget = ""
    for key in ("presmptPrce", "asignBdgtAmt", "purchsBudgetAmt"):
        v = str(item.get(key, "")).strip()
        if v:
            budget = v
            break

    return {
        "title": title or "제목 확인 필요",
        "url": url,
        "source": "pps.data.go.kr",
        "agency": agency,
        "announce_date": announce,
        "close_date": close,
        "budget": budget,
        "snippet": "",
        "attachments": [],
        "content_type": "notice",
        "score": 0.0,
    }

def pps_fetch_bids(
    query: str,
    *,
    page_max: Optional[int] = None,
    rows: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    inqry_div: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    나라장터 입찰공고 목록을 페이지네이션하며 조회.
    - query는 보통 공고명 검색 파라미터로 들어갑니다(PPS_QUERY_PARAM, 기본: bidNtceNm).
    - ENV에서 API 스펙 관련 값을 읽어 유연하게 대응합니다.
    """
    service_key = _get_env("PPS_SERVICE_KEY")
    if not service_key:
        # 키가 없으면 빈 결과 반환(수업 안정성)
        return []

    base_url = _get_env("PPS_BASE_URL", "https://apis.data.go.kr")
    endpoint = _get_env("PPS_ENDPOINT", "/1230000/BidPublicInfoService02/getBidPblancListInfoCnstwk")
    query_param = _get_env("PPS_QUERY_PARAM", "bidNtceNm")

    rows = int(rows or _get_env("PPS_ROWS", "100") or 100)
    page_max = int(page_max or _get_env("PPS_PAGE_MAX", "3") or 3)

    date_from = date_from or _get_env("PPS_DATE_FROM", "")
    date_to = date_to or _get_env("PPS_DATE_TO", "")
    inqry_div = inqry_div or _get_env("PPS_INQRY_DIV", "")

    out: List[Dict[str, Any]] = []
    for page in range(1, page_max + 1):
        params: Dict[str, Any] = {
            "serviceKey": service_key,
            "numOfRows": rows,
            "pageNo": page,
            query_param: query,
        }
        # 날짜/조회구분 등 선택 파라미터(스펙에 존재하는 경우만 서버가 무시하거나 반영)
        if date_from: params.setdefault("inqryBgnDt", date_from)
        if date_to:   params.setdefault("inqryEndDt", date_to)
        if inqry_div: params.setdefault("inqryDiv", inqry_div)

        url = _build_url(base_url, endpoint, params)
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        items = _extract_items(data)

        if not items:
            # 더 이상 없음 → 조기 종료
            break

        for it in items:
            out.append(_to_notice(it))

        # 마지막 페이지 감지(보수적으로 전체 페이지 순회)
        if len(items) < rows:
            break

    # URL 기준 중복 제거
    seen, dedup = set(), []
    for it in out:
        u = it.get("url", "")
        key = (it.get("title",""), u)
        if key in seen:  # 제목+URL 조합
            continue
        seen.add(key)
        dedup.append(it)

    return dedup
