"""验证码识别模块 - AI 识别 + 人工 fallback"""

from __future__ import annotations

import logging

from bili_hardcore.core.bili_client import BiliClient
from bili_hardcore.core.llm_client import llm_client
from bili_hardcore.database import get_setting

logger = logging.getLogger("bili-hardcore")


async def solve_captcha(
    bili: BiliClient,
    captcha_url: str,
) -> tuple[str | None, bool]:
    """
    尝试使用 AI 识别验证码。

    Returns:
        (识别结果, 是否为AI识别) — 如果 AI 识别失败返回 (None, False)
    """
    captcha_model_id = await get_setting("captcha_model_id", "")

    if not captcha_model_id:
        logger.info("未配置验证码识别模型，跳过 AI 识别")
        return None, False

    try:
        logger.info(f"正在使用模型 [{captcha_model_id}] 识别验证码...")
        image_b64 = await bili.download_image_base64(captcha_url)
        result = await llm_client.recognize_captcha(image_b64, captcha_model_id)

        if result and 3 <= len(result) <= 6:
            logger.info(f"AI 识别验证码结果: {result}")
            return result, True
        else:
            logger.warning(f"AI 识别结果格式异常: '{result}'，需要人工输入")
            return None, False
    except Exception as e:
        logger.warning(f"AI 识别验证码失败: {e}，需要人工输入")
        return None, False
