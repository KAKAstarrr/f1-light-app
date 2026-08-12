# -*- coding: utf-8 -*-
"""
config.py — 配置管理

职责：
    集中管理项目所有配置项。开发环境用默认值，生产环境通过 .env 注入。

设计原则：
    - 不把密钥写在代码里，通过环境变量注入
    - 开发用 SQLite，生产用 PostgreSQL，一行 env 切换
"""
import os
from functools import lru_cache


class Settings:
    """项目全局配置（简化版，不依赖 pydantic-settings 以减少安装负担）。

    生产环境通过环境变量覆盖：
        export DATABASE_URL=postgresql://user:pass@host:5432/f1app
        export JWT_SECRET=your-random-secret
    """
    # 数据库
    DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
    DB_PATH = os.path.join(DB_DIR, "f1_app.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

    # JWT 鉴权
    JWT_SECRET = os.environ.get("JWT_SECRET", "f1-light-app-dev-secret-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_DAYS = 7

    # Ergast
    ERGAST_BASE_URL = "https://api.jolpi.ca/ergast/f1"

    # 缓存
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")

    # Fantasy 规则
    FANTASY_BUDGET = 100.0  # 预算上限 ¥100M
    FANTASY_MAX_DRIVERS = 5
    FANTASY_MAX_CONSTRUCTORS = 2

    @property
    def connect_args(self):
        """SQLite 需要这个参数才能在多线程中使用"""
        if "sqlite" in self.DATABASE_URL:
            return {"check_same_thread": False}
        return {}


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
