from fastapi import APIRouter

from app.models.schemas import TaskRequest, TaskResoponse


router = APIRouter()


@router.post("/tasks", response_model= TaskResoponse, status_code=202)
async def create_task(request: TaskRequest) -> TaskResoponse:
    
    
    
    return TaskResoponse(
        task_id="stub-task-id",
        status="accepted",
        message=f"Task recieved: {request.task}"
    )