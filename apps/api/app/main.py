from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.response import ok
from app.modules.aiqa.router import router as aiqa_router
from app.modules.asset.router import router as asset_router
from app.modules.sql.router import router as sql_router
from app.modules.workspace.router import router as workspace_router

app = FastAPI(
    title="DataPlat API",
    version=settings.version,
    description="数据资产 / SQL Gateway / AI 问数",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspace_router, prefix="/api/v1")
app.include_router(asset_router, prefix="/api/v1")
app.include_router(sql_router, prefix="/api/v1")
app.include_router(aiqa_router, prefix="/api/v1")


@app.get("/health")
def health():
    return ok(
        {
            "status": "ok",
            "version": settings.version,
            "env": settings.env,
        }
    )
