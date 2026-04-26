"""FastAPI 应用入口"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from bili_hardcore.api import auth_routes, settings_routes, task_routes, ws_routes
from bili_hardcore.config import APP_HOST, APP_PORT
from bili_hardcore.database import close_db, get_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bili-hardcore")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Bili-Hardcore WebUI 正在启动...")
    await get_db()  # 初始化数据库
    logger.info(f"数据库已初始化")
    yield
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title="Bili-Hardcore",
    description="B站硬核会员自动答题工具 - WebUI",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(auth_routes.router)
app.include_router(settings_routes.router)
app.include_router(task_routes.router)
app.include_router(ws_routes.router)

# 静态文件 & SPA 回退
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    """应用入口点"""
    logger.info(f"启动 Bili-Hardcore WebUI @ http://{APP_HOST}:{APP_PORT}")
    uvicorn.run(
        "bili_hardcore.app:app",
        host=APP_HOST,
        port=APP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
