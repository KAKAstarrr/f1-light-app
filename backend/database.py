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
from sqlalchemy import create_engine, text, inspect
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
    _auto_migrate()


def _auto_migrate():
    """轻量 schema 迁移：对比 ORM 模型与数据库实际列，自动补缺失列。

    为什么需要它？
        SQLite 的 create_all 只会建"不存在的表"，不会给已存在的表加新列。
        如果 models.py 新增了字段（如 User.chip_limitless_used），旧数据库
        会报 "no such column" 导致接口 500。

    原理：
        PRAGMA table_info 拿到实际列 → 与 ORM 模型列对比 → 缺什么补什么。
        只加列、不删列、不改类型，保证向后兼容、不丢数据。

    适合开发阶段；生产环境建议升级到 Alembic 做正式迁移。
    """
    from backend import models  # noqa: F401

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue  # 新表已由 create_all 创建，无需处理
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        missing = [col for col in table.columns if col.name not in existing_cols]
        if not missing:
            continue

        with engine.begin() as conn:
            for col in missing:
                col_type = col.type.compile(dialect=engine.dialect)
                default_sql = ""
                if col.default is not None:
                    # 数值/字符串默认值直接拼 SQL；callable 默认值跳过
                    arg = col.default.arg
                    if isinstance(arg, (int, float, str, bool)):
                        if isinstance(arg, str):
                            default_sql = f" DEFAULT '{arg}'"
                        elif isinstance(arg, bool):
                            default_sql = f" DEFAULT {int(arg)}"
                        else:
                            default_sql = f" DEFAULT {arg}"
                ddl = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}{default_sql}'
                conn.execute(text(ddl))
                print(f"[migrate] 补列 {table_name}.{col.name} {col_type}")
