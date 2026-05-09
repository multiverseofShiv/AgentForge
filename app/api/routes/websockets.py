from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()

@router.websocket("/ws/tasks/{task_id}")
async def task_stream(websocket: WebSocket, task_id:str) -> None:
    await websocket.accept()
    
    try:
        await websocket.send_json(
            {"task_id": task_id, "event":"connected", "message":" stream ready"}
        )
        while True:
            data = await websocket.receive_text()
            await WebSocket.send_json({"echo": data})
            
    except WebSocketDisconnect:
        pass