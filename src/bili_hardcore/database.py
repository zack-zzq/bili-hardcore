"""SQLite 数据库管理模块"""

from __future__ import annotations

import aiosqlite
from bili_hardcore.config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（单例）"""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _init_tables(_db)
    return _db


async def close_db() -> None:
    """关闭数据库连接"""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def _init_tables(db: aiosqlite.Connection) -> None:
    """初始化数据库表"""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            state           TEXT NOT NULL DEFAULT 'pending',
            created_at      TEXT NOT NULL,
            bili_username    TEXT,
            category_ids    TEXT,
            current_question INTEGER NOT NULL DEFAULT 0,
            total_questions  INTEGER NOT NULL DEFAULT 100,
            score           INTEGER NOT NULL DEFAULT 0,
            error_message   TEXT
        );

        CREATE TABLE IF NOT EXISTS task_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id   TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            level     TEXT NOT NULL DEFAULT 'INFO',
            message   TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
    """)
    await db.commit()


# ==================== Settings CRUD ====================

async def get_setting(key: str, default: str = "") -> str:
    """获取设置值"""
    db = await get_db()
    cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row else default


async def set_setting(key: str, value: str) -> None:
    """设置/更新设置值"""
    db = await get_db()
    await db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    await db.commit()


# ==================== Task CRUD ====================

async def create_task(task_id: str, created_at: str) -> None:
    """创建任务记录"""
    db = await get_db()
    await db.execute(
        "INSERT INTO tasks (id, created_at) VALUES (?, ?)",
        (task_id, created_at),
    )
    await db.commit()


async def update_task(task_id: str, **kwargs) -> None:
    """更新任务字段"""
    if not kwargs:
        return
    db = await get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [task_id]
    await db.execute(f"UPDATE tasks SET {sets} WHERE id = ?", values)
    await db.commit()


async def get_task(task_id: str) -> dict | None:
    """获取单个任务"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_tasks() -> list[dict]:
    """获取所有任务（按创建时间倒序）"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_task(task_id: str) -> None:
    """删除任务及其日志"""
    db = await get_db()
    await db.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await db.commit()


# ==================== Task Logs ====================

async def add_task_log(task_id: str, timestamp: str, level: str, message: str) -> None:
    """添加任务日志"""
    db = await get_db()
    await db.execute(
        "INSERT INTO task_logs (task_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
        (task_id, timestamp, level, message),
    )
    await db.commit()


async def get_task_logs(task_id: str, limit: int = 500) -> list[dict]:
    """获取任务日志"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT timestamp, level, message FROM task_logs WHERE task_id = ? ORDER BY id DESC LIMIT ?",
        (task_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]
