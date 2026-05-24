from __future__ import annotations

import json
import logging
from typing import Any


from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from app.agents.state import AgentState
from app.core.config import get_settings
from app.models.schemas import ReviewDecision, SupervisorDecision
from app.prompts.agents import(
    RESEARCHER_SYSTEM,
    SUPERVISOR_SYSTEM,
    WRITER_SYSTEM,
    REVIEWER_SYSTEM,
    SQL_AGENT_SYSTEM,
)
from app.services.llm import get_llm
from app.tools import RESEARCH_TOOLS, SQL_TOOLS


logger = logging.getLogger(__name__)

MAX_REACT_STEPS=2


#shared helpers

def _tool_registry(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {t.name: t for t in tools}



def _execute_tool_calls(
    ai_msg: AIMessage,
    registry: dict[str, BaseTool],
)-> list[ToolMessage]:
    
    results: list[ToolMessage] = []
    for call in ai_msg.tool_calls or []:
        name = call.get("name", "")
        args = call.get("args", {}) or {}
        if isinstance(args, str):
            args = json.loads(args)
        
        call_id = call.get("id", "")
        tool = registry.get(name)
        if tool is None:
            content = f"Tool '{name}' is not availible. Availible: {list(registry)}"
        else:
            try:
                content = tool.invoke(args)
            except Exception as exc:
                logger.exception("Tool %s raised", name)
                content = f"Tool '{name}' raise an Error: {exc}"
        if not isinstance(content, str):
            content = str(content)
        results.append(ToolMessage(content= content, tool_call_id = call_id, name = name ))
    return results


import re
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
)


MAX_REACT_STEPS = 1


def _run_react(
    system_prompt: str,
    user_prompt: str,
    tools: list[BaseTool],
    *,
    temperature: float,
    max_steps: int = MAX_REACT_STEPS,
) -> tuple[str, list[BaseMessage]]:

    llm = get_llm(temperature=temperature)

    tool_registry = {tool.name: tool for tool in tools}

    tool_descriptions = "\n".join(
        f"- {tool.name}: {tool.description}"
        for tool in tools
    )

    # Build the conversation once: system context + user request.
    # We never re-send the full prompt; we only append observations.
    messages: list[BaseMessage] = [
        HumanMessage(content=f"""{system_prompt}

Available tools:
{tool_descriptions}

User request:
{user_prompt}

You may request ONE tool call per turn using EXACTLY this format:

TOOL: tool_name
INPUT: tool input

After receiving a tool result, continue reasoning.
When you have enough information, respond with your final answer directly
(no TOOL/INPUT lines).
""")
    ]

    final_answer = ""

    for step in range(max_steps):
        ai_msg: AIMessage = llm.invoke(messages)
        messages.append(ai_msg)

        content = str(
            ai_msg.content if hasattr(ai_msg, "content") else ai_msg
        ).strip()

        tool_match = re.search(
            r"TOOL:\s*(.+?)\s*\nINPUT:\s*([^\n]+)",
            content,
        )

        # ── Final answer path ──────────────────────────────────────────
        if not tool_match:
            final_answer = content
            break  # <-- this break is what triggers the for/else correctly

        # ── Tool execution path ────────────────────────────────────────
        tool_name  = tool_match.group(1).strip()
        tool_input = tool_match.group(2).strip()[:200]

        tool = tool_registry.get(tool_name)

        if tool is None:
            observation = f"Tool '{tool_name}' not found. Available tools: {list(tool_registry)}"
        else:
            try:
                observation = tool.invoke({
                    "query": tool_input,
                    "max_results": 1,
                    "sentences": 3,
                })
            except Exception as exc:
                logger.exception("Tool %s failed", tool_name)
                observation = f"Tool execution failed: {exc}"

        # Feed the observation back as a HumanMessage so the model can
        # continue reasoning in the next iteration.
        messages.append(
            HumanMessage(
                content=(
                    f"Step {step + 1} observation:\n"
                    f"Tool used: {tool_name}\n"
                    f"Tool input: {tool_input}\n"
                    f"Result:\n{observation}\n\n"
                    "Continue reasoning or provide your final answer."
                )
            )
        )

    else:
        # Only reached if the loop exhausted max_steps without a break
        logger.warning("Reached max ReAct steps (%d)", max_steps)
        final_answer = (
            "Reached maximum reasoning steps without a conclusive answer."
        )

    return final_answer.strip(), messages


# def _run_react(
#     system_prompt: str,
#     user_prompt: str,
#     tools: list[BaseTool],
#     *,
#     temperature: float,
#     max_steps: int = MAX_REACT_STEPS,
# )-> tuple[str, list[BaseMessage]]:
    
    
#     llm = get_llm(temperature=temperature).bind_tools(tools)
#     registry = _tool_registry(tools)
    
    
#     messages: list[BaseMessage] = [
#         SystemMessage(content=system_prompt),
#         HumanMessage(content=user_prompt),
#     ]
    
#     final_text = ""
#     for step in range(max_steps):
#         ai_msg: AIMessage = llm.invoke(messages)
#         messages.append(ai_msg)
        
        
#         if not ai_msg.tool_calls:
#             final_text = ai_msg.content if isinstance(ai_msg, str) else str(ai_msg.content)
#             break
        
#         tool_messages = _execute_tool_calls(ai_msg, registry)
#         messages.extend(tool_messages)
        
#     else:
#         logger.warning("ReAct loop hit max react steps = %d without finishing", max_steps)
#         last_ai = next(
#             (
#                 m for m in reversed(messages) if isinstance(m, AIMessage)
#             ),None,
#         )
#         if last_ai is not None and isinstance(last_ai.content, str):
#             final_text = last_ai.content or "[no final answer produced before step cap]"
#         else:
#             final_text = "[no final answer produced before step cap]"

#     return final_text.strip(), messages



#Supervisor Nodes

MAX_REVISION_ITERATIONS =2

def supervisor_node(state: AgentState) -> dict[str, Any]:
    
    settings = get_settings()
    
    #summary
    parts: list[str] = [f"TASK:\n{state.get('task','')}"]
    
    research_notes = state.get("research_notes", "")
    
    if research_notes:
        parts.append(f"RESEARCH_NOTES (availible):\n{research_notes[:400]}....")
        
    else:
        parts.append("RESEARCH_NOTES: (none yet)")
        
    draft = state.get("draft", "")
    
    if draft:
            parts.append(f"DRAFT (availible):\n {draft[:400]}...")
    else:
        parts.append("DRAFT: (none yet)")
        
    
    review_feedback = state.get("review_feedback", "")
    
    if review_feedback:
        parts.append(f"REVIEW_FEEDBACK:\n{review_feedback}")
        
    iteration_count = state.get("iteration_count", 0)
    parts.append(f"ITERATION_COUNT: {iteration_count} (max{MAX_REVISION_ITERATIONS})")
    
    final_output = state.get("final_output", "")
    if final_output:
        parts.append(f"FINAL_OUTPUT (availible): {final_output[:300]}...")
        
        
    sql_query = state.get("sql_query", "")
    if sql_query:
        parts.append(f"SQL_QUERY: {sql_query}")

    parts.append("Decide which agent should act next. Return your Supervisor Decision now")
    user_prompt = "\n\n".join(parts)
    
    
    llm = get_llm(temperature=settings.temperature_factual).with_structured_output(SupervisorDecision)
    
    decision: SupervisorDecision = llm.invoke(
        [SystemMessage(content=SUPERVISOR_SYSTEM), HumanMessage(content=user_prompt)]
    )    
    
    
    logger.info(
        "Supervisor routed to '%s' - '%s'",
        decision.next_agent,
        decision.reasoning
    )
    
    return{
        "next_agent": decision.next_agent,
        "human_approval_needed": decision.human_approval_needed,
        "message":[
            AIMessage(
                content=f"[Supervisor] -> {decision.next_agent}: {decision.reasoning}"
            ),
        ],
        "status": "done" if decision.next_agent == "FINISH" else "running"
    }


#Researcher

def researcher_node(state: AgentState) -> dict[str, Any]:
    
    settings = get_settings()
    
    task = state.get("task", "")
    
    user_prompt = (
        f"TASK:\n{task}\n\n"
        "Plan the smallest set of tool calls needed, excute tnem, then"
        "produce the structured notes per your system instructions."
    )
    
    notes, trace = _run_react(
        RESEARCHER_SYSTEM,
        user_prompt,
        RESEARCH_TOOLS,
        temperature=settings.temperature_factual
    )
    
    return {
        "research_notes": notes,
        "messages":[trace[1], trace[-1]] if len(trace) >=2 else trace,
        "status":"running",
    }
    
    
#writer

def writer_node(state: AgentState) -> dict[str, Any]:
    
    settings = get_settings()
    task = state.get("task","")
    notes = state.get("research_notes","")
    feedback = state.get("review_feedback","")
    iteration = state.get("iteration_count",0)
    
    parts = [f"TASK:\n{task}", f"RESEARCH_NOTES:\n{notes or '(none yet)'}"]
    
    if feedback:
        parts.append(
            "REVIEW_FEEDBACK (you are revising a prior draft - address every "f"point):\n{feedback}"
        )
        
    parts.append("Write the draft now.")
    user_prompt = "\n\n".join(parts)
    
    
    llm = get_llm(temperature=settings.temperature_creative)
    messages: list[BaseMessage] = [
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=user_prompt),
    ]
    ai_msg = llm.invoke(messages)
    draft = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
    
    
    return{
        "draft": draft.strip(),
        "iteration_count": iteration+1,
        "messages":[messages[-1], ai_msg],
        "status": "running"
    }
    
    
    #Reviewer
    
def reviewer_node(state: AgentState) -> dict[str, Any]:
    settings = get_settings()
    
    task = state.get("task", "")
    notes = state.get("research_notes", "")
    draft = state.get("draft","")
    
    
    user_prompt = (
        f"TASK: \n{task}\n\n"
        f"RESEARCH_NOTES:\n{notes or '(none)'}\n\n"
        f"DRAFT:\n{draft}"
    )
    
    llm = get_llm(temperature=settings.temperature_factual).with_structured_output(ReviewDecision)
    decision: ReviewDecision = llm.invoke([SystemMessage(content=REVIEWER_SYSTEM), HumanMessage(content=user_prompt)])
    
    feedback_text = (
        f"Score: {decision.score}/10 - {'APPROVED' if decision.approved else 'REVISE'}\n"
        f"{decision.feedback}"
    )
    
    return {
        "review_feedback": feedback_text,
        "next_agent":"FINISH" if decision.approved else "writer",
        "status":"running"
    }
    
    
    
#Sql Agent

def sql_agent_node(state: AgentState) -> dict[str, Any]:
    
    settings = get_settings()
    task = state.get("task", "")
    
    user_prompt = (
        f"USER QUESTION:\n{task}\n\n"
        "User `execute_sql` to retrieve the data, then produce the final "
        "answer in the format from our system instructions"
    )
    
    answer, trace = _run_react(
        SQL_AGENT_SYSTEM,
        user_prompt,
        SQL_TOOLS,
        temperature=settings.temperature_factual
    )
    
    
    sql_query, sql_result = _extract_last_sql_pair(trace)
    
    
    return {
        "sql_query": sql_query,
        "sql_result": sql_result,
        "final_output": answer,
        "messages": [trace[1], trace[-1]] if len(trace) >=2 else trace,
        "status":"running"
    }
    
    
    
def _extract_last_sql_pair(trace: list[BaseMessage]) -> tuple[str, str]:
    
    last_query = "",
    last_result = ""
    for msg in reversed(trace):
        if isinstance(msg, ToolMessage) and msg.name == "execute_sql" and not last_result:
            last_result = msg.content if isinstance(msg.content, str) else str(msg.content)
            continue
        if isinstance(msg, AIMessage) and msg.tool_calls and not last_query:
            for call in msg.tool_calls:
                if call.get("name") == "execute_sql":
                    args = call.get("args", {}) or {}
                    last_query = str(args.get("query",""))
                    break
        if last_query and last_result:
            break
    return last_query, last_result
            