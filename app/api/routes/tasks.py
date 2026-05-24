import logging
import uuid
from fastapi import APIRouter, HTTPException


from app.models.schemas import TaskRequest, TaskResoponse

from app.agents.graph import get_compiled_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tasks", response_model= TaskResoponse, status_code=202)
async def create_task(request: TaskRequest) -> TaskResoponse:
    
    task_id = str(uuid.uuid4())
    logger.info("Task %s accepted: %s", task_id, request.task[:80])
    
    
    try:
        graph = get_compiled_graph()
        initial_state = {
            "task": request.task,
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
        
        result = graph.invoke(initial_state)
        
        final_output = (
            result.get("final_output")
            or result.get("draft")
            or "No output produced."
        )
        
        logger.info("Task %s completed - status: %s", task_id, result.get("status"))
        
        return TaskResoponse(
        task_id=task_id,
        status="done",
        message="Task Completed Successfully",
        result= final_output
        
    )
    
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        raise HTTPException(status_code=500, detail = str(exc)) from exc