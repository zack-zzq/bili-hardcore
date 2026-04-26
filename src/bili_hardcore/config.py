"""全局配置模块 - 从环境变量读取配置"""

import os
from pathlib import Path

# ==================== 应用配置 ====================
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8080"))

# ==================== 认证配置 ====================
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", "bili-hardcore-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# ==================== OpenAI Compatible API 配置 ====================
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ==================== 数据目录 ====================
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path.home() / ".bili-hardcore")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bili_hardcore.db"

# ==================== B站 API 配置 ====================
BILI_APPKEY = "783bbb7264451d82"
BILI_APPSEC = "2653583c8873dea268ab9386918b1d65"
BILI_USER_AGENT = "Mozilla/5.0 BiliDroid/1.12.0 (bbcallen@gmail.com)"

BILI_HEADERS = {
    "User-Agent": BILI_USER_AGENT,
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "x-bili-metadata-legal-region": "CN",
    "x-bili-aurora-eid": "",
    "x-bili-aurora-zone": "",
}

# ==================== LLM Prompt 模板 ====================
# "当前时间"用于防止重复prompt被检测触发风控
ANSWER_PROMPT = """\
当前时间：{timestamp}
你是一个高效精准的答题专家，面对选择题时，直接根据问题和选项判断正确答案，并返回对应选项的序号（1, 2, 3, 4）。示例：
问题：大的反义词是什么？
选项：['长', '宽', '小', '热']
回答：3
如果不确定正确答案，选择最接近的选项序号返回，不提供额外解释或超出 1-4 的内容。
---
不要思考，直接回答我的问题：{question}"""

CAPTCHA_PROMPT = """\
请识别这张图片中的验证码文字。验证码通常是4位英文字母或数字的组合。
请只返回识别出的字符，不要包含任何其他文字或解释。"""
