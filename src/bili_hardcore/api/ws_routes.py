"""WebSocket 路由 — 任务实时日志推送"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from bili_hardcore.auth import verify_token
from bili_hardcore.core.task_manager import task_manager

router = APIRouter()


@router.websocket("/ws/task/{task_id}")
async def task_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(""),
):
    """
    WebSocket 端点，用于实时推送任务日志和状态。
    通过 query parameter `token` 进行认证。
    """
    # 验证 token
    username = verify_token(token)
    if not username:
        await websocket.close(code=4001, reason="认证失败")
        return

    ctx = task_manager.get_context(task_id)
    if not ctx:
        await websocket.close(code=4004, reason="任务不存在")
        return

    await websocket.accept()

    # 创建消息队列并订阅
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    ctx.ws_subscribers.append(queue)

    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ctx.ws_subscribers.remove(queue)
