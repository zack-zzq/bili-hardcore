"""任务管理路由"""

import base64
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from bili_hardcore.auth import get_current_user
from bili_hardcore.core.task_manager import task_manager
from bili_hardcore.database import delete_task, get_all_tasks, get_task, get_task_logs
from bili_hardcore.models import (
    CaptchaSubmitRequest,
    CategorySelectRequest,
    TaskInfo,
    TaskListResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("")
async def create_task(_: str = Depends(get_current_user)):
    """创建并启动新的答题任务"""
    task_id = await task_manager.create_task()
    return {"task_id": task_id}


@router.get("", response_model=TaskListResponse)
async def list_tasks(_: str = Depends(get_current_user)):
    """获取所有任务列表"""
    tasks = await get_all_tasks()
    return TaskListResponse(tasks=[TaskInfo(**t) for t in tasks])


@router.get("/qrcode")
async def generate_qrcode(data: str = Query(...), _: str = Depends(get_current_user)):
    """服务端生成二维码图片 (PNG)"""
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_L, box_size=10, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/{task_id}")
async def get_task_detail(task_id: str, _: str = Depends(get_current_user)):
    """获取任务详情（含日志）"""
    t = await get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    logs = await get_task_logs(task_id)
    return {"task": TaskInfo(**t), "logs": logs}


@router.delete("/{task_id}")
async def remove_task(task_id: str, _: str = Depends(get_current_user)):
    """取消并删除任务"""
    await task_manager.cancel_task(task_id)
    await delete_task(task_id)
    return {"status": "ok"}


@router.post("/{task_id}/captcha")
async def submit_captcha(
    task_id: str, req: CaptchaSubmitRequest, _: str = Depends(get_current_user)
):
    """人工提交验证码"""
    if not task_manager.submit_captcha(task_id, req.code):
        raise HTTPException(status_code=400, detail="任务不在等待验证码状态")
    return {"status": "ok"}


@router.post("/{task_id}/category")
async def submit_category(
    task_id: str, req: CategorySelectRequest, _: str = Depends(get_current_user)
):
    """提交分类选择"""
    if not task_manager.submit_category(task_id, req.ids):
        raise HTTPException(status_code=400, detail="任务不在等待选择分类状态")
    return {"status": "ok"}

