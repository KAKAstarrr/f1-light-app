# -*- coding: utf-8 -*-
"""
schemas.py — Pydantic 请求/响应模型

职责：
    定义 API 的请求体和响应体类型，实现：
    1. 自动文档：FastAPI 根据 Pydantic 模型自动生成 Swagger 文档
    2. 类型校验：请求体不符合模型定义时返回 422 + 具体错误
    3. 响应序列化：FastAPI 自动将 Pydantic 模型转为 JSON

为什么需要 Pydantic？
    没有 Pydantic：路由函数收到的是 untyped dict，字段拼错不会报错，调试困难
    有了 Pydantic：IDE 自动补全字段名，拼错编译报错，Swagger 文档有完整 schema
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ============================================================
# 鉴权相关
# ============================================================
class UserRegister(BaseModel):
    """用户注册请求体"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码（至少6位）")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("邮箱格式不正确")
        return v


class UserLogin(BaseModel):
    """用户登录请求体"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


# ============================================================
# Fantasy 相关
# ============================================================
class FantasyDriverPick(BaseModel):
    """选中的车手"""
    driver_code: str = Field(..., description="车手三字母代码，如 VER")
    is_captain: bool = Field(False, description="是否为队长（x2 Boost）")
    price: float = Field(..., description="选取时的价格（M）")


class FantasyConstructorPick(BaseModel):
    """选中的车队"""
    constructor_ref: str = Field(..., description="车队 Ergast ref，如 red_bull")
    price: float = Field(..., description="价格（M）")


class FantasyTeamCreate(BaseModel):
    """创建 Fantasy 阵容请求体"""
    season: int = Field(..., description="赛季年份")
    round: int = Field(..., description="分站序号")
    drivers: list[FantasyDriverPick] = Field(..., description="选中的车手列表（最多5个）")
    constructors: list[FantasyConstructorPick] = Field(..., description="选中的车队列表（最多2个）")
    chip: str = Field("none", description="芯片：none/limitless/wildcard/no_negative")


class FantasyTeamResponse(BaseModel):
    """Fantasy 阵容响应"""
    id: int
    season: int
    round: int
    total_cost: float
    total_points: float
    is_scored: bool
    chip_used: str
    drivers: list[dict]
    constructors: list[dict]


# ============================================================
# 投票相关
# ============================================================
class VoteCreate(BaseModel):
    """投票请求"""
    season: int
    round: int
    driver_code: str = Field(..., description="投票给哪位车手")


# ============================================================
# 预测相关
# ============================================================
class PredictionResponse(BaseModel):
    """AI 预测响应"""
    season: int
    round: int
    model_version: str
    predictions: list[dict]  # [{driver_code, probability, rank_pred, ...}]


# ============================================================
# Fantasy 扩展：芯片 / 联盟 / 定价
# ============================================================
class ChipUseRequest(BaseModel):
    """使用芯片请求"""
    season: int = Field(..., description="赛季年份")
    chip: str = Field(..., description="芯片类型：limitless / wildcard / no_negative")


class LeagueCreateRequest(BaseModel):
    """创建联盟请求"""
    name: str = Field(..., min_length=1, max_length=100, description="联盟名称")
    season: int = Field(..., description="赛季年份")


class LeagueJoinRequest(BaseModel):
    """加入联盟请求"""
    invite_code: str = Field(..., description="邀请码")
