# -*- coding: utf-8 -*-
"""
yfinance 가격 조회 (강사용/답지)
- 목표: 티커 리스트에 대해 현재가/통화를 가져와 표준 형태로 반환
- 주의: 네트워크/방화벽 환경에 따라 yfinance 호출이 실패할 수 있으므로
       실패 케이스를 graceful 하게 처리(에러 필드 포함)합니다.
"""

from typing import List, Dict, Any
import re


def _normalize_symbol(s: str) -> str:
    """
    6자리 숫자면 한국거래소(.KS) 보정.
    예:
      '005930' → '005930.KS'
      'AAPL'   → 'AAPL' (그대로)
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-F-01] 구현 지침
    #  - if re.fullmatch(r"\d{6}", s): return f"{s}.KS"
    #  - else: return s
    # ----------------------------------------------------------------------------
    # 정답 구현:
    if re.fullmatch(r"\d{6}", s):
        return f"{s}.KS"
    return s


def get_quotes(symbols: List[str], timeout: int = 20) -> List[Dict[str, Any]]:
    """
    yfinance로 심볼별 시세를 조회해 리스트로 반환합니다.
    반환 예:
      [{"symbol":"AAPL","price":123.45,"currency":"USD"},
       {"symbol":"005930.KS","price":...,"currency":"KRW"}]
    실패시 해당 심볼은 {"symbol":sym, "error":"..."} 형태로 표기.
    """
    # ----------------------------------------------------------------------------
    # TODO[DAY1-F-02] 구현 지침
    #  1) from yfinance import Ticker 임포트(파일 상단 대신 함수 내부 임포트도 OK)
    #  2) 결과 리스트 out=[]
    #  3) 입력 심볼들을 _normalize_symbol로 보정
    #  4) 각 심볼에 대해:
    #       - t = Ticker(sym)
    #       - 가격: getattr(t.fast_info, "last_price", None) 또는 dict형이면 .get("last_price")
    #       - 통화: getattr(t.fast_info, "currency", None)  또는 dict형이면 .get("currency")
    #       - 둘 다 정상 추출 시 out.append({"symbol": sym, "price": float(price), "currency": cur})
    #       - 예외/누락 시 out.append({"symbol": sym, "error": "설명"})
    #  5) return out
    # ----------------------------------------------------------------------------
    # 정답 구현:
    out: List[Dict[str, Any]] = []
    try:
        # 내부 임포트(강의/실습 환경에서 yfinance 미설치 시, 함수 호출 전 단계에서만 실패하게 함)
        from yfinance import Ticker  # type: ignore
    except Exception as e:
        # yfinance 자체가 없는 경우: 전체 심볼에 동일 오류 표기
        for raw in symbols:
            sym = _normalize_symbol(raw)
            out.append({"symbol": sym, "error": f"ImportError: {type(e).__name__}: {e}"})
        return out

    for raw in symbols:
        sym = _normalize_symbol(raw)
        try:
            t = Ticker(sym)

            # fast_info는 버전에 따라 dict-like 또는 객체 속성일 수 있으므로 모두 안전 처리
            fi = getattr(t, "fast_info", None)

            price = None
            currency = None
            if isinstance(fi, dict):
                price = fi.get("last_price")
                currency = fi.get("currency")
            else:
                # 객체 속성 접근 형태
                price = getattr(fi, "last_price", None)
                currency = getattr(fi, "currency", None)

            # 값 검증 및 캐스팅
            if price is not None:
                try:
                    price = float(price)
                except Exception:
                    # 숫자로 캐스팅 불가 → 실패 처리
                    out.append({"symbol": sym, "error": f"ValueError: invalid price '{price}'"})
                    continue

            if price is None or currency is None:
                out.append({"symbol": sym, "error": "No fast_info (price/currency missing)"})
                continue

            out.append({"symbol": sym, "price": price, "currency": currency})
        except Exception as e:
            out.append({"symbol": sym, "error": f"{type(e).__name__}: {e}"})

    return out
