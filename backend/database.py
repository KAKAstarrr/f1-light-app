# -*- coding: utf-8 -*-
"""
database.py — 数据库连接管理

职责：
    管理 SQLAlchemy 引擎和会话工厂。
    开发阶段用 SQLite（零配置），生产环境切换 PostgreSQL（改 DATABASE_URL 即可）。

核心概念：
    1. Engine：数据库连接池，所有 SQL 操作都通过它发到数据库
    2. SessionLocal：会话工厂，每次请求创建一个独立会话，请求结束关闭
    3. Base：所有 ORM 模型的基类，继承它就能自动建表
    4. get_db()：FastAPI 依赖注入函数，路由用 Depends(get_db) 获取数据库会话
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import settings

# 创建引擎
#   SQLite：文件数据库，零配置，适合开发
#   PostgreSQL：生产环境，支持并发、事务、扩展
engine = create_engine(settings.DATABASE_URL, connect_args=settings.connect_args)

# 会话工厂：每次调用 SessionLocal() 创建一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类：models.py 里的所有表都继承这个类
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：路由里写 `db: Session = Depends(get_db)` 即可拿到会话。

    工作流：
        1. 请求进来 → 生成会话 → 注入路由函数
        2. 路由函数执行完毕 → 关闭会话（finally）
        3. 如果中途出错，会话自动回滚

    用法：
        @app.get("/users")
        def list_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表：读取所有继承 Base 的模型，执行 CREATE TABLE IF NOT EXISTS。

    在 main.py 启动时调用一次即可。已有表不会被重建。
    """
    # 必须先 import models，让 SQLAlchemy 知道所有表定义
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
