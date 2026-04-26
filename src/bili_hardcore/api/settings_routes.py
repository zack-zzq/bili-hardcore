"""设置管理路由"""

from fastapi import APIRouter, Depends

from bili_hardcore.auth import get_current_user
from bili_hardcore.core.llm_client import llm_client
from bili_hardcore.database import get_setting, set_setting
from bili_hardcore.models import Settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=Settings)
async def get_settings(_: str = Depends(get_current_user)):
    """获取当前全局设置"""
    return Settings(
        answer_model_id=await get_setting("answer_model_id", ""),
        captcha_model_id=await get_setting("captcha_model_id", ""),
    )


@router.put("")
async def update_settings(settings: Settings, _: str = Depends(get_current_user)):
    """更新全局设置"""
    await set_setting("answer_model_id", settings.answer_model_id)
    await set_setting("captcha_model_id", settings.captcha_model_id)
    return {"status": "ok"}


@router.get("/models")
async def list_models(_: str = Depends(get_current_user)):
    """获取可用模型列表（代理调用 OpenAI /v1/models）"""
    try:
        models = await llm_client.list_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
