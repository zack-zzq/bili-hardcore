"""B站 API 客户端 - 异步实现

封装所有与 B 站服务端的交互，每个任务实例持有独立的客户端实例（独立登录态）。
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

import httpx

from bili_hardcore.config import BILI_APPKEY, BILI_APPSEC, BILI_HEADERS, BILI_USER_AGENT


class BiliClient:
    """B站 API 客户端 — 每个答题任务持有一个独立实例"""

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.csrf: str | None = None
        self._headers = BILI_HEADERS.copy()
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    # ==================== 签名 ====================

    def _appsign(self, params: dict) -> dict:
        """为请求参数添加 APP 签名"""
        params["ts"] = str(int(time.time()))
        params["appkey"] = BILI_APPKEY
        params = dict(sorted(params.items()))
        query = urllib.parse.urlencode(params)
        sign = hashlib.md5((query + BILI_APPSEC).encode()).hexdigest()
        params["sign"] = sign
        return params

    # ==================== HTTP 封装 ====================

    async def _get(self, url: str, params: dict) -> dict:
        signed = self._appsign(params)
        resp = await self._client.get(url, params=signed, headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, url: str, params: dict) -> dict:
        signed = self._appsign(params)
        resp = await self._client.post(url, data=signed, headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    # ==================== Ticket ====================

    async def get_ticket(self) -> str:
        """获取 bili web ticket"""
        ts = int(time.time())
        key = b"XgwSnGZ1p"
        message = f"ts{ts}".encode()
        hexsign = hmac.new(key, message, hashlib.sha256).hexdigest()

        resp = await self._client.post(
            "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket",
            params={
                "key_id": "ec02",
                "hexsign": hexsign,
                "context[ts]": str(ts),
                "csrf": "",
            },
            headers={"User-Agent": BILI_USER_AGENT},
        )
        resp.raise_for_status()
        return resp.json()["data"]["ticket"]

    # ==================== 登录 ====================

    async def qrcode_get(self) -> dict:
        """获取二维码 URL + auth_code"""
        res = await self._post(
            "https://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code",
            {"local_id": "0"},
        )
        if res.get("code") == 0:
            return res["data"]
        raise RuntimeError(f"获取二维码失败: {res}")

    async def qrcode_poll(self, auth_code: str) -> dict:
        """轮询二维码扫描状态"""
        return await self._post(
            "https://passport.bilibili.com/x/passport-tv-login/qrcode/poll",
            {"auth_code": auth_code, "local_id": "0"},
        )

    def apply_login(self, data: dict) -> dict:
        """应用登录结果，更新内部状态，返回认证信息摘要"""
        self.access_token = data["access_token"]
        mid = str(data["mid"])

        cookies = data["cookie_info"]["cookies"]
        csrf = ""
        for cookie in cookies:
            if cookie["name"] == "bili_jct":
                csrf = cookie["value"]
                break
        self.csrf = csrf

        cookie_str = ";".join(f"{c['name']}={c['value']}" for c in cookies)
        self._headers["x-bili-mid"] = mid
        self._headers["cookie"] = cookie_str

        return {
            "access_token": self.access_token,
            "csrf": self.csrf,
            "mid": mid,
            "cookie": cookie_str,
        }

    # ==================== 用户信息 ====================

    async def get_account_info(self) -> dict:
        """查询当前登录用户信息"""
        res = await self._get(
            "https://app.bilibili.com/x/v2/account/myinfo",
            {"access_key": self.access_token},
        )
        if res.get("code") == 0:
            return res["data"]
        raise RuntimeError(f"获取用户信息失败: {res}")

    # ==================== 硬核会员答题 ====================

    def _senior_params(self, extra: dict | None = None) -> dict:
        """通用的硬核会员 API 参数"""
        params = {
            "access_key": self.access_token,
            "csrf": self.csrf,
            "disable_rcmd": "0",
            "mobi_app": "android",
            "platform": "android",
            "statistics": '{"appId":1,"platform":3,"version":"8.40.0","abtest":""}',
            "web_location": "333.790",
        }
        if extra:
            params.update(extra)
        return params

    async def category_get(self) -> dict:
        """获取答题分类"""
        res = await self._get(
            "https://api.bilibili.com/x/senior/v1/category",
            self._senior_params(),
        )
        if res.get("code") == 0:
            return res["data"]
        if res.get("code") == 41099:
            raise RuntimeError("已达到答题限制 (B站每日限制3次)，请前往B站APP确认")
        raise RuntimeError(f"获取分类失败: {res}")

    async def captcha_get(self) -> dict:
        """获取图形验证码"""
        res = await self._get(
            "https://api.bilibili.com/x/senior/v1/captcha",
            self._senior_params(),
        )
        if res.get("code") == 0:
            return res["data"]
        raise RuntimeError(f"获取验证码失败: {res}")

    async def captcha_submit(self, code: str, captcha_token: str, ids: str) -> bool:
        """提交验证码"""
        res = await self._post(
            "https://api.bilibili.com/x/senior/v1/captcha/submit",
            self._senior_params({
                "bili_code": code,
                "bili_token": captcha_token,
                "gt_challenge": "",
                "gt_seccode": "",
                "gt_validate": "",
                "ids": ids,
                "type": "bilibili",
            }),
        )
        if res.get("code") == 0:
            return True
        raise RuntimeError(f"提交验证码失败: {res}")

    async def question_get(self) -> dict:
        """获取当前题目"""
        return await self._get(
            "https://api.bilibili.com/x/senior/v1/question",
            self._senior_params(),
        )

    async def question_submit(self, qid: int, ans_hash: str, ans_text: str) -> dict:
        """提交答案"""
        return await self._post(
            "https://api.bilibili.com/x/senior/v1/answer/submit",
            self._senior_params({
                "id": str(qid),
                "ans_hash": ans_hash,
                "ans_text": ans_text,
            }),
        )

    async def question_result(self) -> dict:
        """获取答题结果"""
        res = await self._get(
            "https://api.bilibili.com/x/senior/v1/answer/result",
            self._senior_params(),
        )
        if res.get("code") == 0:
            return res["data"]
        raise RuntimeError(f"获取答题结果失败: {res}")

    # ==================== 工具方法 ====================

    async def download_image_base64(self, url: str) -> str:
        """下载图片并返回 base64 编码"""
        import base64
        resp = await self._client.get(url)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode()

    async def init_ticket(self) -> None:
        """初始化 ticket 并更新 headers"""
        ticket = await self.get_ticket()
        self._headers["x-bili-ticket"] = ticket
