"""
麦麦搭子记忆与偏好持久化模块 (McMeal Memory)
基于轻量级 SQLite3 实现用户口味偏好、历史配餐与数据透明度治理
严格遵循隐私安全：支持用户查阅 (view) 与随时清除 (erase)，区分 user-stated 与 system-inferred
"""

import os
import sqlite3
import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class UserPreference:
    """用户偏好项模型"""
    user_id: str
    key: str
    value: str
    source: str  # "user-stated" (用户主动告知) | "system-inferred" (系统根据历史推断)
    updated_at: str

@dataclass
class OrderHistoryRecord:
    """历史配餐记录"""
    record_id: int
    user_id: str
    plan_name: str
    total_amount: float
    items_summary: str
    created_at: str

class McMealMemory:
    """麦麦记忆管理器"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # 默认保存在用户家目录下的 .mcmeal 文件夹
            base_dir = os.path.expanduser("~/.mcmeal")
            os.makedirs(base_dir, exist_ok=True)
            self.db_path = os.path.join(base_dir, "memory.db")
        else:
            self.db_path = db_path
            if self.db_path != ":memory:":
                parent = os.path.dirname(self.db_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not self._conn:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()

    def _init_db(self):
        """初始化数据表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. 用户偏好表 (键值结构，包含来源标注)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    pref_key TEXT NOT NULL,
                    pref_value TEXT NOT NULL,
                    source TEXT NOT NULL CHECK(source IN ('user-stated', 'system-inferred')),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, pref_key)
                )
            """)

            # 2. 确认历史订单表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    items_summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def set_preference(self, user_id: str, key: str, value: str, source: str = "user-stated") -> None:
        """
        保存或更新用户偏好
        :param user_id: 用户唯一标识
        :param key: 偏好键 (如 'spicy_ok', 'dietary_goal', 'fav_burger')
        :param value: 偏好值 (如 'false', 'low_calorie', '双层吉士')
        :param source: 来源标签 ('user-stated' 或 'system-inferred')
        """
        if source not in ("user-stated", "system-inferred"):
            source = "user-stated"
        now_str = datetime.datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_preferences (user_id, pref_key, pref_value, source, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, pref_key) DO UPDATE SET
                    pref_value = excluded.pref_value,
                    source = excluded.source,
                    updated_at = excluded.updated_at
            """, (user_id, key, str(value), source, now_str))
            conn.commit()

    def get_preference(self, user_id: str, key: str) -> Optional[UserPreference]:
        """获取单个偏好"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, pref_key, pref_value, source, updated_at
                FROM user_preferences
                WHERE user_id = ? AND pref_key = ?
            """, (user_id, key))
            row = cursor.fetchone()
            if row:
                return UserPreference(
                    user_id=row["user_id"],
                    key=row["pref_key"],
                    value=row["pref_value"],
                    source=row["source"],
                    updated_at=row["updated_at"]
                )
        return None

    def list_preferences(self, user_id: str) -> List[UserPreference]:
        """列出指定用户的所有存储偏好"""
        results = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, pref_key, pref_value, source, updated_at
                FROM user_preferences
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
            for row in cursor.fetchall():
                results.append(UserPreference(
                    user_id=row["user_id"],
                    key=row["pref_key"],
                    value=row["pref_value"],
                    source=row["source"],
                    updated_at=row["updated_at"]
                ))
        return results

    def erase_preferences(self, user_id: str, key: Optional[str] = None) -> int:
        """
        擦除用户偏好 (完全尊重用户遗忘权/隐私权)
        :param user_id: 用户唯一标识
        :param key: 若指定则只删除该键；若为 None 则清空该用户全部记忆
        :return: 删除的行数
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if key:
                cursor.execute("""
                    DELETE FROM user_preferences
                    WHERE user_id = ? AND pref_key = ?
                """, (user_id, key))
            else:
                cursor.execute("""
                    DELETE FROM user_preferences
                    WHERE user_id = ?
                """, (user_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

    def record_order(self, user_id: str, plan_name: str, total_amount: float, items_summary: str) -> int:
        """记录已采纳的点餐方案"""
        now_str = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO order_history (user_id, plan_name, total_amount, items_summary, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, plan_name, total_amount, items_summary, now_str))
            record_id = cursor.lastrowid
            conn.commit()
            return record_id

    def get_order_history(self, user_id: str, limit: int = 10) -> List[OrderHistoryRecord]:
        """获取用户最近的点餐历史"""
        results = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, plan_name, total_amount, items_summary, created_at
                FROM order_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, limit))
            for row in cursor.fetchall():
                results.append(OrderHistoryRecord(
                    record_id=row["id"],
                    user_id=row["user_id"],
                    plan_name=row["plan_name"],
                    total_amount=row["total_amount"],
                    items_summary=row["items_summary"],
                    created_at=row["created_at"]
                ))
        return results

    def clear_all_data(self, user_id: str) -> None:
        """一键擦除用户的所有偏好与历史数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM order_history WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_context_for_prompt(self, user_id: str) -> str:
        """生成用于注入 Agent 上下文的结构化记忆摘要"""
        prefs = self.list_preferences(user_id)
        if not prefs:
            return ""
        
        lines = ["【用户记忆与长期偏好】:"]
        for p in prefs:
            tag = "用户设定" if p.source == "user-stated" else "系统推断"
            lines.append(f"  • {p.key}: {p.value} ({tag})")
        return "\n".join(lines)
