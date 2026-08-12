from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

import requests
import secrets

# Ergast 基础域名
ERGAST_BASE_URL = "https://api.jolpi.ca/ergast/f1"

# 模块 A 数据源
from backend.data_source import (
    fetch_ergast_current_season, fetch_ergast_season_by_year,
    fetch_ergast_race_result, fetch_ergast_all_circuits,
    fetch_ergast_current_season_drivers, fetch_ergast_season_drivers_by_year,
    fetch_ergast_current_season_driverstandings,
    fetch_ergast_driverstandings_by_year, fetch_ergast_constructorstandings_by_year,
    fetch_ergast_current_season_qualifying_results,
    fetch_ergast_season_qualifying_results_by_year,
    fetch_ergast_current_season_constructorstandings,
    fetch_fastf1_fastest_lap, fetch_fastf1_tyre_strategy,
    fetch_fastf1_telemetry_compare,
    fetch_fastf1_sector_fastest, fetch_fastf1_lap_distribution,
    fetch_fastf1_speed_overlay, fetch_fastf1_track_map, fetch_fastf1_weather,
)

# 模块 C/D 数据库 + 鉴权
from backend.database import engine, get_db, init_db, Base
from backend import models, schemas, auth, game_service, prediction_service

app = FastAPI(
    title="F1 赛车数据互动平台",
    version="0.2.0",
    description="提供赛程/成绩/圈速/轮胎/AI预测/Fantasy/投票的完整后端服务",
)

# CORS：允许前端 dev server 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时自动建表
@app.on_event("startup")
def startup():
    init_db()
    print("[数据库] 表结构初始化完成")


# ============================================================
# 模块 A：基础数据（已实现，保持不变）
# ============================================================
@app.get("/", summary="健康检查")
def index():
    return {"message": "F1 后端服务运行正常", "version": "0.2.0"}

@app.get("/api/current-season", summary="获取当前赛季赛历")
def get_current_season():
    return fetch_ergast_current_season()

@app.get("/api/season/{year}", summary="获取历史赛季赛历")
def get_season_schedule(year: int):
    return fetch_ergast_season_by_year(year)

@app.get("/api/race-result/{year}/{round_num}", summary="获取赛道比赛结果")
def get_race_result(year: int, round_num: int):
    return fetch_ergast_race_result(year, round_num)

@app.get("/api/circuits", summary="获取全部赛道信息")
def get_circuits():
    return fetch_ergast_all_circuits()

@app.get("/api/current/drivers", summary="获取当前赛季车手信息")
def get_current_season_drivers():
    return fetch_ergast_current_season_drivers()

@app.get("/api/{year}/drivers", summary="获取历史赛季车手信息")
def get_season_drivers(year: int):
    return fetch_ergast_season_drivers_by_year(year)

@app.get("/api/current/driverstandings", summary="获取当前赛季车手排名")
def get_current_season_driverstandings():
    return fetch_ergast_current_season_driverstandings()

@app.get("/api/{year}/driverstandings", summary="获取历史赛季车手排名")
def get_driverstandings_by_year(year: int):
    return fetch_ergast_driverstandings_by_year(year)

@app.get("/api/current/constructorstandings", summary="获取当前赛季车队排名")
def get_current_season_constructorstandings():
    return fetch_ergast_current_season_constructorstandings()

@app.get("/api/{year}/constructorstandings", summary="获取历史赛季车队排名")
def get_constructorstandings_by_year(year: int):
    return fetch_ergast_constructorstandings_by_year(year)

@app.get("/api/current/{round_num}/qualifying", summary="获取当前赛季分站排位赛结果")
def get_current_qualifying(round_num: int):
    return fetch_ergast_current_season_qualifying_results(round_num)

@app.get("/api/{year}/{round_num}/qualifying", summary="获取历史赛季分站排位赛结果")
def get_qualifying_by_year(year: int, round_num: int):
    return fetch_ergast_season_qualifying_results_by_year(year, round_num)

@app.get("/api/fastf1/{year}/{round}/fast-lap", summary="单场车手最快圈排行")
def get_fastf1_fastest_lap(year: int, round: int, session_type: str = 'R'):
    return fetch_fastf1_fastest_lap(year, round, session_type)

@app.get("/api/fastf1/{year}/{round}/tyre-strategy", summary="单站轮胎策略")
def api_tyre_strategy(year: int, round: int):
    return fetch_fastf1_tyre_strategy(year, round)

@app.get("/api/fastf1/{year}/{round}/telemetry", summary="多车手遥测对比（模块 B2）")
def get_telemetry_compare(
    year: int, round: int,
    drivers: str = Query(..., description="车手代码，逗号分隔，如 VER,NOR"),
    channels: str = Query("speed,throttle", description="通道，逗号分隔"),
    session_type: str = Query("R", description="会话类型 R=正赛 Q=排位 FP1/FP2/FP3=练习赛 SQ=冲刺排位 SS=冲刺赛")
):
    driver_list = [d.strip().upper() for d in drivers.split(",") if d.strip()][:3]
    channel_list = [c.strip().lower() for c in channels.split(",") if c.strip()]
    if not driver_list:
        raise HTTPException(status_code=400, detail="至少选择一个车手")
    if not channel_list:
        raise HTTPException(status_code=400, detail="至少选择一个通道")
    return fetch_fastf1_telemetry_compare(year, round, driver_list, channel_list, session_type)


@app.get("/api/fastf1/{year}/{round}/sector-fastest", summary="赛道分段最快（模块 B1）")
def get_sector_fastest(year: int, round: int, session_type: str = 'R'):
    """各分段（Sector 1/2/3）最快车手及时间排行。"""
    return fetch_fastf1_sector_fastest(year, round, session_type)


@app.get("/api/fastf1/{year}/{round}/lap-distribution", summary="圈速分布（模块 B3）")
def get_lap_distribution(year: int, round: int, session_type: str = 'R'):
    """全部车手圈速分布数据，用于箱线图可视化。"""
    return fetch_fastf1_lap_distribution(year, round, session_type)


@app.get("/api/fastf1/{year}/{round}/speed-overlay", summary="速度叠加对比（模块 B4）")
def get_speed_overlay(
    year: int, round: int,
    drivers: str = Query(..., description="车手代码，逗号分隔，如 VER,NOR"),
    session_type: str = Query("R", description="会话类型")
):
    """基于赛道距离归一化的多车手速度曲线叠加。"""
    driver_list = [d.strip().upper() for d in drivers.split(",") if d.strip()][:4]
    if not driver_list:
        raise HTTPException(status_code=400, detail="至少选择一个车手")
    return fetch_fastf1_speed_overlay(year, round, driver_list, session_type)


@app.get("/api/fastf1/{year}/{round}/track-map", summary="赛道地图分段着色（模块 B5）")
def get_track_map(year: int, round: int, session_type: str = 'R'):
    """赛道坐标 + 各分段最快车手着色数据。"""
    return fetch_fastf1_track_map(year, round, session_type)


@app.get("/api/fastf1/{year}/{round}/weather", summary="天气数据（模块 B6）")
def get_weather(year: int, round: int, session_type: str = 'R'):
    """比赛天气数据（Rainfall/AirTemp/TrackTemp/Humidity）。"""
    return fetch_fastf1_weather(year, round, session_type)


# ============================================================
# 模块 3A：用户注册 / 登录（JWT）
# ============================================================
@app.post("/api/auth/register", response_model=schemas.TokenResponse, summary="用户注册")
def register(req: schemas.UserRegister, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    if db.query(models.User).filter(models.User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = models.User(
        username=req.username,
        email=req.email,
        password_hash=auth.hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth.create_access_token({"sub": user.username, "user_id": user.id})
    return schemas.TokenResponse(
        access_token=token,
        username=user.username,
        user_id=user.id,
    )


@app.post("/api/auth/login", response_model=schemas.TokenResponse, summary="用户登录")
def login(req: schemas.UserLogin, db: Session = Depends(get_db)):
    # 支持用户名或邮箱登录
    user = db.query(models.User).filter(
        (models.User.username == req.username) | (models.User.email == req.username)
    ).first()
    if not user or not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = auth.create_access_token({"sub": user.username, "user_id": user.id})
    return schemas.TokenResponse(
        access_token=token,
        username=user.username,
        user_id=user.id,
    )


@app.get("/api/auth/me", summary="获取当前用户信息")
def get_me(user: models.User = Depends(auth.get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


# ============================================================
# 模块 3B：AI 预测
# ============================================================
@app.get("/api/prediction/{year}/{round}", summary="AI 夺冠概率预测")
def get_prediction(year: int, round: int):
    result = prediction_service.predict_race(year, round)
    return result


# ============================================================
# 模块 3C：Fantasy 阵容
# ============================================================
@app.post("/api/fantasy/team", summary="创建/更新 Fantasy 阵容")
def create_fantasy_team(
    req: schemas.FantasyTeamCreate,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # 校验阵容
    valid, total_cost, msg = game_service.validate_team_budget(
        [{"driver_code": d.driver_code, "price": d.price} for d in req.drivers],
        [{"constructor_ref": c.constructor_ref, "price": c.price} for c in req.constructors],
        req.chip
    )
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # 检查是否已有阵容（每人每站一份）
    existing = db.query(models.FantasyTeam).filter(
        models.FantasyTeam.user_id == user.id,
        models.FantasyTeam.season == req.season,
        models.FantasyTeam.round == req.round
    ).first()

    if existing:
        # 更新：先删旧关联
        db.query(models.FantasyTeamDriver).filter(
            models.FantasyTeamDriver.team_id == existing.id
        ).delete()
        db.query(models.FantasyTeamConstructor).filter(
            models.FantasyTeamConstructor.team_id == existing.id
        ).delete()
        team = existing
        team.chip_used = req.chip
        team.total_cost = total_cost
    else:
        team = models.FantasyTeam(
            user_id=user.id,
            season=req.season,
            round=req.round,
            chip_used=req.chip,
            total_cost=total_cost,
        )
        db.add(team)
        db.flush()

    # 写入车手
    for pick in req.drivers:
        db.add(models.FantasyTeamDriver(
            team_id=team.id,
            driver_code=pick.driver_code,
            is_captain=pick.is_captain,
            price=pick.price
        ))

    # 写入车队
    for pick in req.constructors:
        db.add(models.FantasyTeamConstructor(
            team_id=team.id,
            constructor_ref=pick.constructor_ref,
            price=pick.price
        ))

    db.commit()
    db.refresh(team)

    return {
        "id": team.id,
        "season": team.season,
        "round": team.round,
        "total_cost": team.total_cost,
        "total_points": team.total_points,
        "chip_used": team.chip_used,
        "is_scored": team.is_scored,
        "message": "阵容保存成功",
    }


@app.get("/api/fantasy/team/{season}/{round}", summary="查看我的阵容")
def get_my_fantasy_team(
    season: int,
    round: int,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    team = db.query(models.FantasyTeam).filter(
        models.FantasyTeam.user_id == user.id,
        models.FantasyTeam.season == season,
        models.FantasyTeam.round == round
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="未找到阵容")

    return {
        "id": team.id,
        "season": team.season,
        "round": team.round,
        "total_cost": team.total_cost,
        "total_points": team.total_points,
        "chip_used": team.chip_used,
        "is_scored": team.is_scored,
        "drivers": [
            {"code": d.driver_code, "is_captain": d.is_captain, "price": d.price}
            for d in team.drivers
        ],
        "constructors": [
            {"ref": c.constructor_ref, "price": c.price}
            for c in team.constructors
        ],
    }


@app.post("/api/fantasy/score/{season}/{round}", summary="结算 Fantasy 积分（管理员）")
def score_fantasy(
    season: int,
    round: int,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """根据比赛结果自动结算 Fantasy 积分。"""
    # 获取比赛结果
    try:
        race_data = fetch_ergast_race_result(season, round)
        results = race_data.get("Races", [{}])[0].get("Results", [])
    except Exception:
        raise HTTPException(status_code=500, detail="无法获取比赛结果")

    # 获取最快圈车手
    fastest_lap_code = ""
    for r in results:
        if r.get("FastestLap", {}).get("rank") == "1":
            fastest_lap_code = r.get("Driver", {}).get("code", "")
            break

    # 获取所有该站的阵容
    teams = db.query(models.FantasyTeam).filter(
        models.FantasyTeam.season == season,
        models.FantasyTeam.round == round,
        models.FantasyTeam.is_scored == False
    ).all()

    scored = []
    for team in teams:
        team_drivers = [
            {"driver_code": d.driver_code, "is_captain": d.is_captain, "price": d.price}
            for d in team.drivers
        ]
        team_constructors = [
            {"constructor_ref": c.constructor_ref, "price": c.price}
            for c in team.constructors
        ]

        score = game_service.calculate_team_points(
            team_drivers, team_constructors, results, fastest_lap_code, team.chip_used
        )
        team.total_points = score["total_points"]
        team.is_scored = True
        scored.append({
            "team_id": team.id,
            "user_id": team.user_id,
            "total_points": score["total_points"],
            "details": score["driver_details"],
        })

    db.commit()
    return {
        "code": 200,
        "season": season,
        "round": round,
        "scored_teams": len(scored),
        "results": scored,
    }


@app.get("/api/fantasy/leaderboard/{season}", summary="Fantasy 赛季排行榜")
def get_fantasy_leaderboard(season: int, db: Session = Depends(get_db)):
    """赛季 Fantasy 积分排行榜。"""
    from sqlalchemy import func

    rows = db.query(
        models.FantasyTeam.user_id,
        models.User.username,
        func.sum(models.FantasyTeam.total_points).label("season_points"),
        func.count(models.FantasyTeam.id).label("rounds_scored"),
    ).join(
        models.User, models.FantasyTeam.user_id == models.User.id
    ).filter(
        models.FantasyTeam.season == season,
        models.FantasyTeam.is_scored == True,
    ).group_by(
        models.FantasyTeam.user_id, models.User.username
    ).order_by(
        func.sum(models.FantasyTeam.total_points).desc()
    ).all()

    return {
        "season": season,
        "leaderboard": [
            {
                "rank": i + 1,
                "user_id": row.user_id,
                "username": row.username,
                "season_points": float(row.season_points or 0),
                "rounds_scored": int(row.rounds_scored or 0),
            }
            for i, row in enumerate(rows)
        ],
    }


# ============================================================
# 模块 3C 扩展：动态定价 / 历史记录 / 芯片 / 联盟
# ============================================================
@app.get("/api/fantasy/prices", summary="获取车手/车队动态定价")
def get_fantasy_prices(
    season: int = Query(..., description="赛季年份"),
    db: Session = Depends(get_db)
):
    """根据 PRD 3.3.3 动态定价算法，返回全部车手和车队的当前价格。"""
    from backend.data_source import fetch_ergast_driverstandings_by_year, fetch_ergast_constructorstandings_by_year

    # 获取上赛季积分榜（用于 base_price）
    last_year = season - 1
    last_standings_raw = fetch_ergast_driverstandings_by_year(last_year)
    last_standings = []
    if isinstance(last_standings_raw, dict):
        sl = last_standings_raw.get("StandingsLists", [])
        if sl:
            last_standings = sl[0].get("DriverStandings", [])

    # 构建上赛季排名映射
    last_rank_map = {}
    for d in last_standings:
        code = d.get("Driver", {}).get("code", "")
        if code:
            last_rank_map[code] = int(d.get("position", 99))

    # 当前赛季积分榜
    current_standings_raw = fetch_ergast_driverstandings_by_year(season)
    current_standings = []
    if isinstance(current_standings_raw, dict):
        sl = current_standings_raw.get("StandingsLists", [])
        if sl:
            current_standings = sl[0].get("DriverStandings", [])

    max_points = max((float(d.get("points", 0)) for d in current_standings), default=1) or 1

    # 计算车手价格
    driver_prices = []
    for d in current_standings:
        code = d.get("Driver", {}).get("code", "")
        if not code:
            continue
        name = f"{d.get('Driver', {}).get('givenName', '')} {d.get('Driver', {}).get('familyName', '')}"
        points = float(d.get("points", 0))
        wins = int(d.get("wins", 0))
        position = int(d.get("position", 99))
        constructor = d.get("Constructors", [{}])[0].get("name", "Unknown")
        last_rank = last_rank_map.get(code, 0)

        price = game_service.calculate_driver_price(
            season_points=points,
            max_season_points=max_points,
            recent_avg_position=position,
            dnf_count=0,
            last_season_rank=last_rank,
        )

        driver_prices.append({
            "code": code,
            "name": name,
            "constructor": constructor,
            "price": price,
            "season_points": points,
            "wins": wins,
            "position": position,
        })

    # 车队价格（基于积分排名简单定价）
    constructor_prices = []
    ctor_raw = fetch_ergast_constructorstandings_by_year(season)
    if isinstance(ctor_raw, dict):
        sl = ctor_raw.get("StandingsLists", [])
        if sl:
            for c in sl[0].get("ConstructorStandings", []):
                ref = c.get("Constructor", {}).get("constructorId", "")
                name = c.get("Constructor", {}).get("name", "")
                pos = int(c.get("position", 99))
                points = float(c.get("points", 0))

                if pos <= 2:
                    price = 25.0
                elif pos <= 4:
                    price = 20.0
                elif pos <= 6:
                    price = 15.0
                else:
                    price = 10.0

                constructor_prices.append({
                    "ref": ref,
                    "name": name,
                    "price": price,
                    "season_points": points,
                    "position": pos,
                })

    return {
        "code": 200,
        "season": season,
        "drivers": driver_prices,
        "constructors": constructor_prices,
    }


@app.get("/api/fantasy/history", summary="查看历史阵容记录")
def get_fantasy_history(
    season: int = Query(..., description="赛季年份"),
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """查看当前用户指定赛季的全部 Fantasy 阵容与得分明细。"""
    teams = db.query(models.FantasyTeam).filter(
        models.FantasyTeam.user_id == user.id,
        models.FantasyTeam.season == season,
    ).order_by(models.FantasyTeam.round.asc()).all()

    return {
        "season": season,
        "total_rounds": len(teams),
        "total_points": sum(t.total_points for t in teams if t.is_scored),
        "history": [
            {
                "round": t.round,
                "total_cost": t.total_cost,
                "total_points": t.total_points,
                "is_scored": t.is_scored,
                "chip_used": t.chip_used,
                "transfers_used": t.transfers_used,
                "drivers": [
                    {"code": d.driver_code, "is_captain": d.is_captain, "price": d.price}
                    for d in t.drivers
                ],
                "constructors": [
                    {"ref": c.constructor_ref, "price": c.price}
                    for c in t.constructors
                ],
            }
            for t in teams
        ],
    }


@app.post("/api/fantasy/chip", summary="使用芯片")
def use_chip(
    req: schemas.ChipUseRequest,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """使用 Fantasy 芯片（赛季维度计数，Limitless/Wildcard 各 2 次，No Negative 1 次）。"""
    chip_limits = {
        "limitless": 2,
        "wildcard": 2,
        "no_negative": 1,
    }

    chip_field_map = {
        "limitless": "chip_limitless_used",
        "wildcard": "chip_wildcard_used",
        "no_negative": "chip_no_negative_used",
    }

    if req.chip not in chip_limits:
        raise HTTPException(status_code=400, detail="无效的芯片类型")

    field = chip_field_map[req.chip]
    used = getattr(user, field, 0)
    if used >= chip_limits[req.chip]:
        raise HTTPException(
            status_code=400,
            detail=f"{req.chip} 芯片已用完（上限 {chip_limits[req.chip]} 次）"
        )

    setattr(user, field, used + 1)
    db.commit()

    return {
        "message": f"芯片 {req.chip} 使用成功",
        "chip": req.chip,
        "used_count": used + 1,
        "remaining": chip_limits[req.chip] - used - 1,
    }


@app.get("/api/fantasy/chip-status", summary="查看芯片使用状态")
def get_chip_status(
    season: int = Query(..., description="赛季年份"),
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """查看当前用户各芯片的剩余使用次数。"""
    return {
        "season": season,
        "limitless": {"used": user.chip_limitless_used or 0, "max": 2},
        "wildcard": {"used": user.chip_wildcard_used or 0, "max": 2},
        "no_negative": {"used": user.chip_no_negative_used or 0, "max": 1},
    }


# ---- 联盟系统 ----
@app.post("/api/fantasy/leagues", summary="创建联盟")
def create_league(
    req: schemas.LeagueCreateRequest,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """创建 Fantasy 联盟，返回邀请码。"""
    invite_code = secrets.token_urlsafe(8)[:10].upper()

    league = models.League(
        name=req.name,
        invite_code=invite_code,
        creator_id=user.id,
        season=req.season,
    )
    db.add(league)
    db.flush()

    # 创建者自动加入
    db.add(models.LeagueMembership(league_id=league.id, user_id=user.id))
    db.commit()
    db.refresh(league)

    return {
        "id": league.id,
        "name": league.name,
        "invite_code": league.invite_code,
        "season": league.season,
        "message": "联盟创建成功",
    }


@app.post("/api/fantasy/leagues/{league_id}/join", summary="加入联盟")
def join_league(
    league_id: int,
    req: schemas.LeagueJoinRequest,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """通过邀请码加入 Fantasy 联盟。"""
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        raise HTTPException(status_code=404, detail="联盟不存在")

    if league.invite_code != req.invite_code:
        raise HTTPException(status_code=400, detail="邀请码错误")

    # 检查是否已加入
    existing = db.query(models.LeagueMembership).filter(
        models.LeagueMembership.league_id == league_id,
        models.LeagueMembership.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已加入该联盟")

    # 检查人数上限
    count = db.query(models.LeagueMembership).filter(
        models.LeagueMembership.league_id == league_id
    ).count()
    if count >= league.max_members:
        raise HTTPException(status_code=400, detail="联盟人数已满")

    db.add(models.LeagueMembership(league_id=league_id, user_id=user.id))
    db.commit()

    return {"message": f"成功加入联盟: {league.name}"}


@app.get("/api/fantasy/leagues/{league_id}/leaderboard", summary="联盟内排行榜")
def get_league_leaderboard(
    league_id: int,
    db: Session = Depends(get_db)
):
    """获取联盟内 Fantasy 积分排行榜。"""
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        raise HTTPException(status_code=404, detail="联盟不存在")

    from sqlalchemy import func

    # 查询联盟成员的 Fantasy 总分
    rows = db.query(
        models.User.id,
        models.User.username,
        func.sum(models.FantasyTeam.total_points).label("season_points"),
        func.count(models.FantasyTeam.id).label("rounds_scored"),
    ).join(
        models.LeagueMembership, models.LeagueMembership.user_id == models.User.id
    ).outerjoin(
        models.FantasyTeam, models.FantasyTeam.user_id == models.User.id
    ).filter(
        models.LeagueMembership.league_id == league_id,
        models.FantasyTeam.season == league.season,
        models.FantasyTeam.is_scored == True,
    ).group_by(
        models.User.id, models.User.username
    ).order_by(
        func.sum(models.FantasyTeam.total_points).desc()
    ).all()

    return {
        "league_id": league_id,
        "league_name": league.name,
        "season": league.season,
        "member_count": db.query(models.LeagueMembership).filter(
            models.LeagueMembership.league_id == league_id
        ).count(),
        "leaderboard": [
            {
                "rank": i + 1,
                "user_id": r.id,
                "username": r.username,
                "season_points": float(r.season_points or 0),
                "rounds_scored": int(r.rounds_scored or 0),
            }
            for i, r in enumerate(rows)
        ],
    }


@app.get("/api/fantasy/my-leagues", summary="查看我加入的联盟")
def get_my_leagues(
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """查看当前用户加入的全部联盟。"""
    memberships = db.query(models.LeagueMembership).filter(
        models.LeagueMembership.user_id == user.id
    ).all()

    leagues = []
    for m in memberships:
        league = m.league
        member_count = db.query(models.LeagueMembership).filter(
            models.LeagueMembership.league_id == league.id
        ).count()
        leagues.append({
            "id": league.id,
            "name": league.name,
            "invite_code": league.invite_code if league.creator_id == user.id else None,
            "season": league.season,
            "member_count": member_count,
            "is_creator": league.creator_id == user.id,
        })

    return {"leagues": leagues}


# ============================================================
# 模块 E：投票系统
# ============================================================
@app.post("/api/vote", summary="最佳车手投票")
def cast_vote(
    req: schemas.VoteCreate,
    user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # 唯一性约束：每人每站每种投票类型只能投一次
    existing = db.query(models.Vote).filter(
        models.Vote.user_id == user.id,
        models.Vote.season == req.season,
        models.Vote.round == req.round,
        models.Vote.vote_type == "driver_of_day"
    ).first()

    if existing:
        # 更新投票
        existing.driver_code = req.driver_code
        existing.voted_at = datetime.utcnow()
        db.commit()
        return {"message": "投票已更新", "driver_code": req.driver_code}
    else:
        vote = models.Vote(
            user_id=user.id,
            season=req.season,
            round=req.round,
            driver_code=req.driver_code,
        )
        db.add(vote)
        db.commit()
        return {"message": "投票成功", "driver_code": req.driver_code}


@app.get("/api/vote/results/{season}/{round_num}", summary="查看投票结果")
def get_vote_results(season: int, round_num: int, db: Session = Depends(get_db)):
    """获取指定分站投票统计（饼图数据）。"""
    from sqlalchemy import func

    results = db.query(
        models.Vote.driver_code,
        func.count(models.Vote.id).label("vote_count")
    ).filter(
        models.Vote.season == season,
        models.Vote.round == round_num,
        models.Vote.vote_type == "driver_of_day"
    ).group_by(
        models.Vote.driver_code
    ).order_by(
        func.count(models.Vote.id).desc()
    ).all()

    total = sum(r[1] for r in results)
    return {
        "season": season,
        "round": round_num,
        "total_votes": total,
        "results": [
            {
                "driver_code": r[0],
                "votes": int(r[1]),
                "percentage": round(int(r[1]) / total * 100, 1) if total > 0 else 0,
            }
            for r in results
        ],
    }
