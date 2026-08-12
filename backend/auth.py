# -*- coding: utf-8 -*-
"""
auth.py — JWT 鉴权服务

职责：
    用户注册、登录、JWT Token 签发与校验、密码哈希（bcrypt）。

核心概念：
    1. 密码不能明文存储 —— 用 bcrypt 单向哈希，不可逆
    2. JWT (JSON Web Token) —— 服务端签名的字符串，客户端每次请求带在 Header 里
    3. 无状态鉴权 —— 服务端不保存 session，只验证 JWT 签名是否合法 + 是否过期

工作流：
    注册：用户名/密码 → bcrypt 哈希 → 存入数据库
    登录：验证密码 → 签发 JWT（含 user_id, username, 过期时间）
    鉴权：客户端 Header: Authorization: Bearer <token> → 解码 JWT → 取出 user_id

FastAPI 依赖注入：
    路由写法：def me(user: User = Depends(get_current_user))
    get_current_user 会自动解码 JWT 并查询用户，未登录返回 401
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User

# OAuth2 令牌提取器：从 Authorization: Bearer <token> 中提取 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """把明文密码转成 bcrypt 哈希。

    bcrypt 每次哈希会随机生成 salt，所以同一个密码两次哈希结果不同。
    验证时用 verify_password(明文, 哈希) 即可。

    注意：bcrypt 有 72 字节限制，超长密码截断到 72。
    """
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码是否匹配哈希值。"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """签发 JWT Token。

    参数：
        data: 要编码进 token 的数据，通常 {"sub": username, "user_id": 1}
        expires_delta: 过期时间，默认 7 天

    返回：
        JWT 字符串，客户端放在 Authorization: Bearer <token> 头里

    Token 解码后包含：
        - sub: 用户名
        - user_id: 用户 ID
        - exp: 过期时间（Unix 时间戳）
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.JWT_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI 依赖注入：从 JWT 解析当前登录用户。

    用法：
        @app.get("/me")
        def my_profile(user: User = Depends(get_current_user)):
            return {"username": user.username}

    未登录或 token 过期 → 401 Unauthorized
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据，请先登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """可选鉴权：带 token 就解析，没带就返回 None。用于投票等接口。"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id:
            return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        pass
    return None
