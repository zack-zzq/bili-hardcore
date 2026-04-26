# syntax=docker/dockerfile:1

# ==================== Build Stage ====================
FROM python:3.13-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 复制依赖声明并安装
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# 复制源代码并安装项目
COPY README.md ./
COPY src/ src/
RUN uv sync --frozen --no-dev --no-editable

# ==================== Runtime Stage ====================
FROM python:3.13-slim AS runtime

# 安全：创建非 root 用户
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# 从 builder 拷贝虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data

# 创建数据目录
RUN mkdir -p /app/data && chown -R app:app /app

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/api/auth/verify', timeout=5)" || exit 1

CMD ["bili-hardcore"]
