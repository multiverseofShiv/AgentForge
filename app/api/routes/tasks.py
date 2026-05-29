import logging
from typing import Any
import uuid
from fastapi import APIRouter, HTTPException


from app.models.schemas import ApproveRequest, TaskRequest, TaskResoponse

from app.agents.graph import get_compiled_graph, get_hitl_graph

logger = logging.getLogger(__name__)

router = APIRouter()

_graph = get_hitl_graph()

def _initial_state(task: str) -> dict[str, Any]:
    return {
            "task": task,
            "message":[],
            "research_notes":"",
            "draft":"",
            "review_feedback":"",
            "sql_query":"",
            "sql_result":"",
            "final_output":"",
            "next_agent":"",
            "iteration_count":0,
            "human_approval_needed":False,
            "status":"running"
        }

def _extract_output(state: dict[str, Any])-> str:
    return(
        state.get("final_output")
        or state.get("draft")
        or "No output produced"
    )
    
    
def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id":thread_id}}



@router.post("/tasks", response_model= TaskResoponse, status_code=202)
async def create_task(request: TaskRequest) -> TaskResoponse:
    
    task_id = str(uuid.uuid4())
    logger.info("Task %s accepted: %s", task_id, request.task[:80])
    
    
    try:
        config = _thread_config(task_id)
        result = _graph.invoke(_initial_state(request.task), config)
        
        snapshot = _graph.get_state(config)
        
        if snapshot.next:
            
            pending_node = snapshot.next[0] if snapshot.next else "unknown"
            logger.info("Task %s interrupted before '%s' - awaiting human approval",
                        task_id, 
                        pending_node,
            )
            return TaskResoponse(
                task_id=task_id,
                status="awaiting_approval",
                message=f"Paused before '{pending_node}'. POST /tasks/{task_id}/approve to continue.",
            )
        
        logger.info("Task %s completed - status: %s", task_id, result.get("status"))
        
        return TaskResoponse(
        task_id=task_id,
        status="done",
        message="Task Completed Successfully",
        result= _extract_output(result),
    )
    
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        raise HTTPException(status_code=500, detail = str(exc)) from exc
    
    
@router.post("/tasks/{task_id}/approve", response_model = TaskResoponse)
async def approve_task(task_id: str, body: ApproveRequest) -> TaskResoponse:
    
    config = _thread_config(task_id)
    
    snapshot = _graph.set_state(config)
    if not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail=f"task '{task_id}' is not awaiting approval (no pending nodes).",
        )
        
    if not body.approved:
        logger.info("Task %s rejected by human - aborting", task_id)
        return TaskResoponse(
            task_id=task_id,
            status="done",
            message="Task aborted by human decision",
            result= _extract_output(snapshot.values),
        )
    
    logger.info("Task %s approved by human resuming", task_id)
    
    try:
        
        result = _graph.invoke(None, config)
        
        snapshot = _graph.get_state(config)
        if snapshot.next:
            pending_node = snapshot.next[0]
            logger.info("Task '%s' interrupted again '%s'", task_id, pending_node)
            return TaskResoponse(
            task_id=task_id,
            status="awaiting_approval",
            message=f"Paused before '{pending_node}'.  POST /tasks/{task_id}/approve to continue",
        )
        
        
        logger.info("Task %s completed after approval", task_id)
        return TaskResoponse(
                task_id=task_id,
                status="done",
                message="Task aborted by human decision",
                result= _extract_output(snapshot.values),
            )
    
    except Exception as exc:
        logger.exception("Task %s failed after approval", task_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    