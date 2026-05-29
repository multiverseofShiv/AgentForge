from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from AgentForge.app.api.routes import websocket
from app.api.routes import tasks
from app.core.config import get_settings

settings = get_settings()

app =  FastAPI(
    title="AgentForge",
    description="Multi-agent orchestration platform powered by langgraph",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status" : "ok", "env": settings.app_env}