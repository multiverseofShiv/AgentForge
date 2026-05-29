from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from __future__ import annotations

import json
import logging
import uuid

router = APIRouter()

from app.agents.graph import get_hitl_graph

logger = logging.getLogger(__name__)

router = APIRouter()

_graph = get_hitl_graph

_INTERESTING_EVENTS = {
    "on_chain_start",
    "on_chain_end",
    "on_tool_start",
    "on_tool_end",
    "on_chat_model_stream",
}

_NODE_LABELS = {
    "supervisor" : "Supervisor",
    "researcher" : "Researcher",
    "writer" : "Writer",
    "reviewer" : "Reviewer",
    "sql_agent": "SQL Agent",
}

def _make_event(event_type: str, **kwargs)->dict:
    return {"event": event_type, **kwargs}



@router.websocket("/ws/tasks/{task_id}")
async def task_stream(websocket: WebSocket, task_id:str) -> None:
    
    await websocket.accept()
    logger.info("WebSocket connected - task_id=%s", task_id)
    
    try:
        await websocket.send_json(_make_event("connected", task_id=task_id))
        
        raw = await websocket.receive_text()
        data = json.loads(raw)
        task_text = data.get("task", "")
        if not task_text:
            await websocket.send_json(
                _make_event("error", message="Missing 'task' field in payload")
            )
            await websocket.close()
            return

        thread_id = task_id if task_id != "new" else str(uuid.uuid4())
        config = {"configurable" : {"thread_id": "thread_id"}}
        
        await websocket.send_json(
            _make_event("task_started", task_id=thread_id, task= task_text)
        )
        
        initial_state = {
            "task": task_text,
            "message":[],
            "research_notes": "",
            "draft": "",
            "review_feedback": "",
            "sql_query":"",
            "sql_result":"",
            "final_output": "",
            "next_agent":"",
            "iteration_count":0,
            "human_approval_needed":False,
            "status":"running",
        }
        
        async for event in _graph.astream_events(
            initial_state, config = config, version="v2"
        ):  
            kind = event.get("event", "")
            name = event.get("name", "")
            
            if kind not in _INTERESTING_EVENTS:
                    continue
                
            
            if kind == "on_chain_start" and name in _NODE_LABELS:
                await websocket.send_json(
                    _make_event(
                        "node_start",
                        node = name,
                        label = _NODE_LABELS[name],
                    )
                )
            
            elif kind == "on_chain_end" and name in _NODE_LABELS:
                output = event.get("data",{}).get("output", {})
                summary = {}
                if name == "supervisor":
                    summary["next_agent"] = output.get("next_agent", "")
                elif name == "reviewer":
                    feedback = output.get("review_feedback", "")
                    summary["review_feedback"] = feedback[:200] if feedback else ""
                elif name=="writer":
                    summary["iteration"] = output.get("iteration_count",0)
                    
                    
                await websocket.send_json(
                    _make_event(
                        "node_end",
                        node = name,
                        label = _NODE_LABELS[name],
                        summary = summary,
                    )
                )
                
                
            elif kind == "on_tool_start":
                tool_input = event.get("data", {}).get("input", {})
                await websocket.send_json(
                    _make_event(
                        "tool_start",
                        tool=name,
                        input=str(tool_input)[:300],
                    )
                )
                
            elif kind == "on_tool_end":
                chunk = event.get("data", {}).get("chunk",None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await websocket.send_json(
                        _make_event("llm_token", token = chunk.content)
                    )
                    
            snapshot = _graph.get_state(config)
            final_state = snapshot.values if snapshot else {}
            final_output = (
                final_state.get(final_output)
                or final_state.get("draft")
                or "No output produced"
            )
            
            if snapshot and snapshot.next:
                await websocket.send_json(
                    _make_event(
                        "awaiting_approval",
                        task_id = thread_id,
                        pending_node = snapshot.next[0]
                    )
                )
            else:
                await websocket.send_json("task_done",task_id=thread_id, result = final_output)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected - task_id=%s", task_id)
    except Exception:
        logger.exception("WebSocket error - task_id=%s", task_id)
        try:
            await websocket.send_json(
                _make_event("error", message="Internal Server Error")
            )
        except Exception:
            pass