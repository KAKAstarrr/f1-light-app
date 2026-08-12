# -*- coding: utf-8 -*-
"""
models.py — SQLAlchemy ORM 模型

职责：
    定义数据库表结构，每张表对应一个 Python 类。
    完整 ER 设计见 study/04_数据库设计.md。

为什么用 ORM 而不是手写 SQL？
    1. 代码可读性：User.query.filter_by(username="admin").first() 比 SQL 直觉
    2. 类型安全：字段类型在 Python 层面有定义，拼错字段名会报错
    3. 自动建表：Base.metadata.create_all() 一行代码创建所有表
    4. 跨数据库：同一套代码，SQLite/PostgreSQL/MySQL 只改连接串
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    """用户表 — 注册/登录/JWT 鉴权"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(100))
    role = Column(String(20), default="user")  # user / admin
    created_at = Column(DateTime, default=datetime.utcnow)

    # 芯片使用计数（赛季维度，每次使用 +1，赛季重置时归零）
    chip_limitless_used = Column(Integer, default=0)
    chip_wildcard_used = Column(Integer, default=0)
    chip_no_negative_used = Column(Integer, default=0)

    # 关系：一个用户有多份 Fantasy 阵容
    fantasy_teams = relationship("FantasyTeam", back_populates="user", cascade="all, delete-orphan")
    league_memberships = relationship("LeagueMembership", back_populates="user", cascade="all, delete-orphan")


class Driver(Base):
    """车手表 — 从 Ergast 同步"""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    driver_ref = Column(String(50), unique=True, nullable=False)  # Ergast driverId
    name = Column(String(100), nullable=False)
    code = Column(String(3))  # 三字母缩写 VER
    number = Column(Integer)
    nationality = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Constructor(Base):
    """车队表"""
    __tablename__ = "constructors"

    id = Column(Integer, primary_key=True, index=True)
    constructor_ref = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class FantasyTeam(Base):
    """Fantasy 阵容 — 每人每站一份"""
    __tablename__ = "fantasy_teams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    chip_used = Column(String(20), default="none")  # none / limitless / wildcard / no_negative
    total_cost = Column(Float, default=0.0)
    total_points = Column(Float, default=0.0)
    is_scored = Column(Boolean, default=False)  # 是否已结算
    transfers_used = Column(Integer, default=0)  # 本站已用转会次数
    created_at = Column(DateTime, default=datetime.utcnow)

    # 唯一约束：每人每站只能有一份阵容
    __table_args__ = (
        UniqueConstraint("user_id", "season", "round", name="uq_fantasy_team_user_round"),
    )

    user = relationship("User", back_populates="fantasy_teams")
    drivers = relationship("FantasyTeamDriver", back_populates="team", cascade="all, delete-orphan")
    constructors = relationship("FantasyTeamConstructor", back_populates="team", cascade="all, delete-orphan")


class FantasyTeamDriver(Base):
    """阵容-车手关联（多对多）"""
    __tablename__ = "fantasy_team_drivers"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("fantasy_teams.id", ondelete="CASCADE"), nullable=False)
    driver_code = Column(String(10), nullable=False)  # 用车手三字母代码关联
    is_captain = Column(Boolean, default=False)  # x2 Boost
    price = Column(Float, nullable=False)  # 选取时的价格

    team = relationship("FantasyTeam", back_populates="drivers")
    __table_args__ = (
        UniqueConstraint("team_id", "driver_code", name="uq_ftd_team_driver"),
    )


class FantasyTeamConstructor(Base):
    """阵容-车队关联"""
    __tablename__ = "fantasy_team_constructors"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("fantasy_teams.id", ondelete="CASCADE"), nullable=False)
    constructor_ref = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)

    team = relationship("FantasyTeam", back_populates="constructors")
    __table_args__ = (
        UniqueConstraint("team_id", "constructor_ref", name="uq_ftc_team_constructor"),
    )


class Prediction(Base):
    """AI 预测记录 — 每站每车手一条"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    driver_code = Column(String(10), nullable=False)
    probability = Column(Float, nullable=False)  # 夺冠概率 0-1
    rank_pred = Column(Integer, nullable=False)  # 预测排名
    model_version = Column(String(20), default="rule_v1")
    features_json = Column(Text)  # 特征快照
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("season", "round", "driver_code", name="uq_pred_round_driver"),
        Index("idx_pred_round", "season", "round"),
    )


class Vote(Base):
    """投票表 — 最佳车手投票"""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    driver_code = Column(String(10), nullable=False)
    vote_type = Column(String(30), default="driver_of_day")
    voted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "season", "round", "vote_type", name="uq_vote_user_round_type"),
        Index("idx_vote_round", "season", "round", "vote_type"),
    )


class League(Base):
    """Fantasy 联盟表"""
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(20), unique=True, nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    season = Column(Integer, nullable=False)
    max_members = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    creator = relationship("User", foreign_keys=[creator_id])
    memberships = relationship("LeagueMembership", back_populates="league", cascade="all, delete-orphan")


class LeagueMembership(Base):
    """联盟成员关联表（多对多）"""
    __tablename__ = "league_memberships"

    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    league = relationship("League", back_populates="memberships")
    user = relationship("User", back_populates="league_memberships")

    __table_args__ = (
        UniqueConstraint("league_id", "user_id", name="uq_league_user"),
    )
