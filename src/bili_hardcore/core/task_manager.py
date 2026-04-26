"""并行任务管理器

管理多个答题任务的生命周期，每个任务在独立的 asyncio.Task 中运行。
通过 WebSocket 向前端广播日志和状态变更。
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from time import time

from bili_hardcore.core.bili_client import BiliClient
from bili_hardcore.core.captcha_solver import solve_captcha
from bili_hardcore.core.llm_client import llm_client
from bili_hardcore.database import (
    add_task_log,
    create_task,
    get_setting,
    update_task,
)
from bili_hardcore.models import TaskState, WSMessage, WSMessageType

logger = logging.getLogger("bili-hardcore")


class TaskContext:
    """单个任务的运行上下文"""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.bili = BiliClient()
        self.state = TaskState.PENDING
        self.asyncio_task: asyncio.Task | None = None
        self.ws_subscribers: list[asyncio.Queue] = []
        # 保存二维码 URL 以便后续连接的客户端获取
        self.qr_url: str | None = None
        # 用于人工交互的 Future
        self._captcha_future: asyncio.Future | None = None
        self._category_future: asyncio.Future | None = None

    async def broadcast(self, msg: WSMessage) -> None:
        """向所有订阅此任务的 WebSocket 客户端广播消息"""
        for q in self.ws_subscribers:
            try:
                q.put_nowait(msg.model_dump())
            except asyncio.QueueFull:
                pass

    async def log(self, message: str, level: str = "INFO") -> None:
        """记录日志并广播"""
        ts = datetime.now(timezone.utc).isoformat()
        await add_task_log(self.task_id, ts, level, message)
        await self.broadcast(WSMessage(
            type=WSMessageType.LOG,
            data={"timestamp": ts, "level": level, "message": message},
        ))

    async def set_state(self, state: TaskState) -> None:
        """更新状态并广播"""
        self.state = state
        await update_task(self.task_id, state=state.value)
        await self.broadcast(WSMessage(
            type=WSMessageType.STATUS_CHANGE,
            data={"state": state.value},
        ))

    async def cleanup(self) -> None:
        await self.bili.close()


class TaskManager:
    """全局任务管理器"""

    def __init__(self) -> None:
        self.tasks: dict[str, TaskContext] = {}

    async def create_task(self) -> str:
        """创建并启动一个新的答题任务"""
        task_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        await create_task(task_id, now)

        ctx = TaskContext(task_id)
        self.tasks[task_id] = ctx
        ctx.asyncio_task = asyncio.create_task(self._run_task(ctx))
        return task_id

    def get_context(self, task_id: str) -> TaskContext | None:
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        ctx = self.tasks.get(task_id)
        if ctx and ctx.asyncio_task and not ctx.asyncio_task.done():
            ctx.asyncio_task.cancel()
            await ctx.set_state(TaskState.CANCELLED)
            await ctx.cleanup()
            return True
        return False

    def submit_captcha(self, task_id: str, code: str) -> bool:
        ctx = self.tasks.get(task_id)
        if ctx and ctx._captcha_future and not ctx._captcha_future.done():
            ctx._captcha_future.set_result(code)
            return True
        return False

    def submit_category(self, task_id: str, ids: str) -> bool:
        ctx = self.tasks.get(task_id)
        if ctx and ctx._category_future and not ctx._category_future.done():
            ctx._category_future.set_result(ids)
            return True
        return False

    # ==================== 任务主流程 ====================

    async def _run_task(self, ctx: TaskContext) -> None:
        try:
            # 1. 登录
            await self._phase_login(ctx)
            # 2. 验证用户等级
            await self._phase_validate(ctx)
            # 3. 获取分类 & 验证码
            await self._phase_verification(ctx)
            # 4. 答题
            await self._phase_answering(ctx)
            # 5. 完成
            await ctx.set_state(TaskState.COMPLETED)
            await ctx.log("🎉 答题任务已完成")
        except asyncio.CancelledError:
            await ctx.log("任务已取消", "WARNING")
        except Exception as e:
            await ctx.set_state(TaskState.FAILED)
            await update_task(ctx.task_id, error_message=str(e))
            await ctx.log(f"任务失败: {e}", "ERROR")
        finally:
            await ctx.cleanup()

    # ----- Phase: 登录 -----
    async def _phase_login(self, ctx: TaskContext) -> None:
        await ctx.set_state(TaskState.QR_LOGIN)
        await ctx.log("正在初始化登录...")
        await ctx.bili.init_ticket()

        qr_data = await ctx.bili.qrcode_get()
        url = qr_data["url"]
        auth_code = qr_data["auth_code"]

        await ctx.log("请使用哔哩哔哩APP扫描二维码登录")
        ctx.qr_url = url
        await ctx.broadcast(WSMessage(
            type=WSMessageType.QR_CODE,
            data={"url": url},
        ))

        # 轮询二维码扫描
        for _ in range(120):
            await asyncio.sleep(1)
            try:
                poll = await ctx.bili.qrcode_poll(auth_code)
                if poll.get("code") == 0:
                    auth_info = ctx.bili.apply_login(poll["data"])
                    await ctx.broadcast(WSMessage(type=WSMessageType.QR_SCANNED, data=None))
                    await ctx.log("登录成功 ✅")
                    # 获取用户名
                    try:
                        info = await ctx.bili.get_account_info()
                        uname = info.get("name", "")
                        if uname:
                            await update_task(ctx.task_id, bili_username=uname)
                            await ctx.log(f"当前用户: {uname}")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        raise RuntimeError("二维码登录超时 (120秒)")

    # ----- Phase: 验证等级 -----
    async def _phase_validate(self, ctx: TaskContext) -> None:
        await ctx.log("正在验证用户等级...")
        info = await ctx.bili.get_account_info()
        level = info.get("level", 0)
        if level < 6:
            raise RuntimeError(f"当前用户等级为 {level}，需要 6 级才能参与答题")
        await ctx.log(f"用户等级: {level} ✅")

    # ----- Phase: 验证码 & 分类选择 -----
    async def _phase_verification(self, ctx: TaskContext) -> None:
        await ctx.set_state(TaskState.SELECTING_CATEGORY)
        await ctx.log("正在获取答题分类...")

        categories = await ctx.bili.category_get()
        cat_list = [{"id": c["id"], "name": c["name"]} for c in categories.get("categories", [])]
        await ctx.broadcast(WSMessage(type=WSMessageType.CATEGORIES, data=cat_list))
        await ctx.log("请选择答题分类 (最多3个)")

        # 等待用户选择分类
        ctx._category_future = asyncio.get_event_loop().create_future()
        ids = await ctx._category_future
        ctx._category_future = None
        await update_task(ctx.task_id, category_ids=ids)
        await ctx.log(f"已选择分类: {ids}")

        # 获取验证码
        await ctx.set_state(TaskState.CAPTCHA)
        await ctx.log("正在获取验证码...")
        captcha_data = await ctx.bili.captcha_get()
        captcha_url = captcha_data["url"]
        captcha_token = captcha_data["token"]

        # 尝试 AI 识别
        code, is_ai = await solve_captcha(ctx.bili, captcha_url)

        if code and is_ai:
            # AI 识别出结果，尝试提交
            await ctx.log(f"AI 识别验证码: {code}，正在提交...")
            try:
                await ctx.bili.captcha_submit(code, captcha_token, ids)
                await ctx.log("验证码验证通过 (AI 识别) ✅")
                await ctx.broadcast(WSMessage(
                    type=WSMessageType.CAPTCHA_RESULT,
                    data={"success": True, "code": code, "source": "ai"},
                ))
                return
            except Exception as e:
                await ctx.log(f"AI 识别的验证码提交失败: {e}，切换到人工输入", "WARNING")

        # fallback: 人工输入
        await ctx.set_state(TaskState.CAPTCHA_MANUAL)
        # 下载验证码图片并发给前端
        try:
            img_b64 = await ctx.bili.download_image_base64(captcha_url)
        except Exception:
            img_b64 = ""
        await ctx.broadcast(WSMessage(
            type=WSMessageType.CAPTCHA,
            data={"url": captcha_url, "image_base64": img_b64},
        ))
        await ctx.log("⚠️ 请在界面中输入验证码")

        # 等待人工输入 (最多5分钟)
        ctx._captcha_future = asyncio.get_event_loop().create_future()
        try:
            code = await asyncio.wait_for(ctx._captcha_future, timeout=300)
        except asyncio.TimeoutError:
            raise RuntimeError("验证码输入超时 (5分钟)")
        finally:
            ctx._captcha_future = None

        await ctx.log(f"人工输入验证码: {code}，正在提交...")
        await ctx.bili.captcha_submit(code, captcha_token, ids)
        await ctx.log("验证码验证通过 ✅")
        await ctx.broadcast(WSMessage(
            type=WSMessageType.CAPTCHA_RESULT,
            data={"success": True, "code": code, "source": "manual"},
        ))

    # ----- Phase: 答题 -----
    async def _phase_answering(self, ctx: TaskContext) -> None:
        await ctx.set_state(TaskState.ANSWERING)
        await ctx.log("开始答题...")

        model_id = await get_setting("answer_model_id", "")
        if not model_id:
            raise RuntimeError("未配置答题模型 ID，请先在设置中选择")

        question_num = 0
        current_score = 0

        while question_num < 100:
            # 获取题目
            q_resp = await ctx.bili.question_get()

            if q_resp.get("code") != 0:
                await ctx.log("需要重新验证，但答题中不应出现此状态", "WARNING")
                break

            data = q_resp.get("data", {})
            question = data.get("question", "")
            answers = data.get("answers", [])
            qid = data.get("id")
            question_num = data.get("question_num", question_num + 1)

            await update_task(ctx.task_id, current_question=question_num)

            # 显示题目
            opts = "\n".join(f"  {i}. {a['ans_text']}" for i, a in enumerate(answers, 1))
            await ctx.log(f"第{question_num}题: {question}")
            await ctx.broadcast(WSMessage(
                type=WSMessageType.QUESTION,
                data={"num": question_num, "question": question,
                      "answers": [a["ans_text"] for a in answers]},
            ))

            # AI 回答
            retry_count = 0
            while True:
                try:
                    prompt = f"题目:{question}\n答案:{answers}"
                    raw_answer = await llm_client.ask(prompt, model_id, str(time()))
                    raw_answer = raw_answer.strip()
                    await ctx.log(f"AI 回答: {raw_answer}")

                    # 解析答案
                    answer_idx = self._parse_answer(raw_answer, len(answers))
                    if answer_idx is None:
                        await ctx.log(f"AI 回复了无关内容，正在重试...", "WARNING")
                        retry_count += 1
                        if retry_count > 5:
                            await ctx.log("重试次数过多，跳过此题", "ERROR")
                            break
                        continue
                    break
                except Exception as e:
                    retry_count += 1
                    sleep_time = math.pow(2, min(retry_count + 1, 7))
                    await ctx.log(f"AI 回答出错: {e}，{sleep_time:.0f}秒后重试...", "WARNING")
                    if retry_count > 7:
                        raise RuntimeError("AI 回答失败次数过多")
                    await asyncio.sleep(sleep_time)

            if answer_idx is None:
                continue

            # 提交答案
            chosen = answers[answer_idx - 1]
            result = await ctx.bili.question_submit(qid, chosen["ans_hash"], chosen["ans_text"])

            if result.get("code") == 41103:
                await ctx.log("答案提交失败: 可能已经是硬核会员或答题已结束", "ERROR")
                break
            elif result.get("code") != 0:
                await ctx.log(f"答案提交失败: {result}", "ERROR")
                continue

            # 获取得分
            score_data = await ctx.bili.question_result()
            score = score_data.get("score", 0)
            accuracy = (score / question_num) * 100 if question_num > 0 else 0

            if score > current_score:
                await ctx.log(f"回答正确 ✅ 得分:{score} 正确率:{accuracy:.1f}%")
            else:
                await ctx.log(f"回答错误 ❌ 得分:{score} 正确率:{accuracy:.1f}%")
            current_score = score

            await update_task(ctx.task_id, score=score)
            await ctx.broadcast(WSMessage(
                type=WSMessageType.ANSWER,
                data={"num": question_num, "correct": score > current_score - 1,
                      "score": score, "accuracy": round(accuracy, 1)},
            ))

        # 打印最终结果
        await ctx.log("========== 答题结果 ==========")
        try:
            result = await ctx.bili.question_result()
            score = result.get("score", 0)
            await update_task(ctx.task_id, score=score)
            await ctx.log(f"总分: {score}")
            for cs in result.get("scores", []):
                await ctx.log(f"  {cs['category']}: {cs['score']}/{cs['total']}")
            if score >= 60:
                await ctx.log("🎉🎉🎉 恭喜您通过了答题！🎉🎉🎉")
            else:
                await ctx.log("未能通过答题，建议尝试知识区或历史区")
            await ctx.broadcast(WSMessage(type=WSMessageType.RESULT, data=result))
        except Exception as e:
            await ctx.log(f"获取结果失败: {e}", "ERROR")

    @staticmethod
    def _parse_answer(answer: str, num_options: int) -> int | None:
        try:
            idx = int(answer)
        except ValueError:
            match = re.search(r"回答[:：]\s*(\d+)", answer)
            if not match:
                # 尝试找到任意单个数字
                digits = re.findall(r"\d+", answer)
                if len(digits) == 1:
                    idx = int(digits[0])
                else:
                    return None
            else:
                idx = int(match.group(1))
        if 1 <= idx <= num_options:
            return idx
        return None


# 全局任务管理器单例
task_manager = TaskManager()
