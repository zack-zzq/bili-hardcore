"""Pydantic 数据模型定义"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


# ==================== 认证 ====================
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ==================== 设置 ====================
class Settings(BaseModel):
    answer_model_id: str = ""
    captcha_model_id: str = ""


# ==================== 任务 ====================
class TaskState(str, Enum):
    PENDING = "pending"
    QR_LOGIN = "qr_login"
    SELECTING_CATEGORY = "selecting_category"
    CAPTCHA = "captcha"
    CAPTCHA_MANUAL = "captcha_manual"
    ANSWERING = "answering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCreate(BaseModel):
    """创建任务时不需要额外参数，分类在流程中选择"""
    pass


class TaskInfo(BaseModel):
    id: str
    state: str
    created_at: str
    bili_username: str | None = None
    category_ids: str | None = None
    current_question: int = 0
    total_questions: int = 100
    score: int = 0
    error_message: str | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskInfo]


class CategoryItem(BaseModel):
    id: int
    name: str


class CategoryListResponse(BaseModel):
    categories: list[CategoryItem]


class CaptchaSubmitRequest(BaseModel):
    code: str


class CategorySelectRequest(BaseModel):
    ids: str  # 逗号分隔的分类 ID


# ==================== WebSocket 消息 ====================
class WSMessageType(str, Enum):
    LOG = "log"
    QR_CODE = "qr_code"
    QR_SCANNED = "qr_scanned"
    CATEGORIES = "categories"
    CAPTCHA = "captcha"
    CAPTCHA_RESULT = "captcha_result"
    STATUS_CHANGE = "status_change"
    QUESTION = "question"
    ANSWER = "answer"
    RESULT = "result"
    ERROR = "error"


class WSMessage(BaseModel):
    type: WSMessageType
    data: dict | list | str | None = None
