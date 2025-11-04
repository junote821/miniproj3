# -*- coding: utf-8 -*-
"""
루트 오케스트레이터 (강사용/답지 버전)
- 목표: 서브 에이전트(Day1/Day2/Day3)를 도구로 연결하고, 프롬프트/모델을 설정
- 학생용의 TODO 마커/설명을 유지하고 각 TODO에 '정답 구현'을 채워 넣었습니다.
"""

from __future__ import annotations
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm

# 서브 에이전트(도구) — 각 day의 agent.py에서 정의되어 있다고 가정
from sub_agents.day1.agent import day1_web_agent
from sub_agents.day2.agent import day2_rag_agent
from sub_agents.day3.agent import day3_gov_agent

# 프롬프트(설명/규칙)
from .prompts import ORCHESTRATOR_DESC, ORCHESTRATOR_PROMPT


# ------------------------------------------------------------------------------
# TODO[ROOT-A-01] 모델 선택:
#  - 경량 LLM을 선택하여 LiteLlm(model="...")로 초기화
#  - 예: "openai/gpt-4o-mini"
# ------------------------------------------------------------------------------
# 정답 구현:
MODEL: Optional[LiteLlm] = LiteLlm(model="openai/gpt-4o-mini")


# ------------------------------------------------------------------------------
# TODO[ROOT-A-02] 루트 에이전트 구성:
#  요구:
#   - name: Pydantic 제약(영문/숫자/언더스코어만) → 예: "KT_AIVLE_Orchestrator"
#   - model: 위 MODEL 사용
#   - description/instruction: prompts.py에서 작성한 상수 사용
#   - tools: Day1/Day2/Day3를 AgentTool로 감싸 순서대로 등록
#   - before/after 콜백은 필요 없음(기본 LLM-Tool 루프)
# ------------------------------------------------------------------------------
# 정답 구현:
root_agent = Agent(
    name="KT_AIVLE_Orchestrator",
    model=MODEL,
    description=ORCHESTRATOR_DESC,
    instruction=ORCHESTRATOR_PROMPT,
    tools=[
        AgentTool(agent=day1_web_agent),
        AgentTool(agent=day2_rag_agent),
        AgentTool(agent=day3_gov_agent),
    ],
)
