# -*- coding: utf-8 -*-
"""
루트 오케스트레이터 (강사용/답지)
- Day1/Day2/Day3(Gov) + Day3(PPS-나라장터) 툴 연결
"""
from __future__ import annotations
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm

# 기존 서브 에이전트
from student.day1.agent import day1_web_agent
from student.day2.agent import day2_rag_agent
from student.day3.agent import day3_gov_agent


from .prompts import ORCHESTRATOR_DESC, ORCHESTRATOR_PROMPT

MODEL: Optional[LiteLlm] = LiteLlm(model="openai/gpt-4o-mini")

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
