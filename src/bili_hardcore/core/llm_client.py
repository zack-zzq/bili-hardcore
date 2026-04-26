"""OpenAI Compatible LLM 客户端

统一的 LLM 接口，支持文本问答和图像识别（验证码）。
Base URL 和 API Key 通过环境变量配置。
"""

from __future__ import annotations

import httpx

from bili_hardcore.config import ANSWER_PROMPT, CAPTCHA_PROMPT, OPENAI_API_KEY, OPENAI_BASE_URL


class LLMClient:
    """OpenAI Compatible API 客户端"""

    def __init__(self) -> None:
        self.base_url = OPENAI_BASE_URL.rstrip("/") if OPENAI_BASE_URL else ""
        self.api_key = OPENAI_API_KEY
        self._client = httpx.AsyncClient(timeout=60.0)

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _check_config(self) -> None:
        if not self.base_url or not self.api_key:
            raise RuntimeError("LLM 未配置: 请设置环境变量 OPENAI_BASE_URL 和 OPENAI_API_KEY")

    # ==================== 模型列表 ====================

    async def list_models(self) -> list[dict]:
        """获取可用模型列表 (GET /v1/models)"""
        self._check_config()
        resp = await self._client.get(
            f"{self.base_url}/models",
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenAI 格式返回 {"data": [...]}
        models = data.get("data", [])
        return [{"id": m["id"], "owned_by": m.get("owned_by", "")} for m in models]

    # ==================== 文本问答 (答题) ====================

    async def ask(self, question: str, model_id: str, timestamp: str) -> str:
        """
        向 LLM 提问，返回模型的文本回答。

        Args:
            question: 格式化后的题目 + 选项文本
            model_id: 模型 ID
            timestamp: 当前时间戳（用于防风控）
        """
        self._check_config()
        if not model_id:
            raise RuntimeError("未配置答题模型 ID，请在设置中选择")

        prompt = ANSWER_PROMPT.format(timestamp=timestamp, question=question)

        resp = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ==================== 图像识别 (验证码) ====================

    async def recognize_captcha(self, image_base64: str, model_id: str) -> str:
        """
        使用视觉模型识别验证码图片。

        Args:
            image_base64: 图片的 base64 编码
            model_id: 支持视觉输入的模型 ID

        Returns:
            识别出的验证码字符
        """
        self._check_config()
        if not model_id:
            raise RuntimeError("未配置验证码识别模型 ID，请在设置中选择")

        resp = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": CAPTCHA_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                },
                            },
                        ],
                    }
                ],
            },
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        # 清理结果，只保留字母数字
        cleaned = "".join(c for c in result.strip() if c.isalnum())
        return cleaned


# 全局 LLM 客户端单例
llm_client = LLMClient()
