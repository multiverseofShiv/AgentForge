from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.agents.nodes import(
    MAX_REVISION_ITERATIONS,
    researcher_node,
    reviewer_node,
    sql_agent_node,
    supervisor_node,
    writer_node,
)

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

def _route_supervisor(state: AgentState) -> str:
    
    next_agent = state.get("next_agent", "FINISH")
    iteration_count = state.get("iteration_count", 0)
    
    if next_agent == "writer" and iteration_count >= MAX_REVISION_ITERATIONS:
        logger.warning(
            "Iteration Cap reached (%d/%d) - overriding '%s' -> 'FINISH'",
            iteration_count,
            MAX_REVISION_ITERATIONS,
            next_agent, 
        )
        return "FINISH"
    
    logger.debug("Routing from supervisor -> %s", next_agent)
    return next_agent


def build_graph() -> StateGraph:
    
    
    graph = StateGraph(AgentState)
    
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher",researcher_node)
    graph.add_node("writer",writer_node)
    graph.add_node("reviewer",reviewer_node)
    graph.add_node("sql_agent",sql_agent_node)
    
    
    #entry point
    graph.set_entry_point("supervisor")
    
    
    graph.add_conditional_edges("supervisor", _route_supervisor,{"researcher":"researcher","writer":"writer", "reviewer":"reviewer","sql_agent":"sql_agent","FINISH":END},)
    
    for worker in ("researcher","writer","reviewer","sql_agent"):
        graph.add_edge(worker, "supervisor")

    return graph


def get_compiled_graph():
    
    graph = build_graph()
    compiled = graph.compile()
    logger.info("AgentForge graph compiled - nodes: %s", list(compiled.nodes))
    return compiled    


def get_hitl_graph():
    
    from langgraph.checkpoint.memory import MemorySaver
    
    graph = build_graph()
    checkpointer = MemorySaver()
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["sql_agent"],
    )
    
    logger.info("AgentForge Graph Compiled (HITL) - nodes: %s, interrupt_before: ['sql_agent']",
                list(compiled.nodes),
                )
    return compiled