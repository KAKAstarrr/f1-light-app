# -*- coding: utf-8 -*-
"""第五部分：阶段 3 数据库 / 认证 / Fantasy / 规则预测"""

PART3_INTRO = (
    "本部分对应项目「阶段 3：数据库与 AI 预测」全部知识点：SQLAlchemy ORM、8 张表设计、"
    "唯一约束与自动迁移、FastAPI 依赖注入、配置管理、bcrypt 密码哈希、JWT 无状态鉴权、"
    "Pydantic 进阶、Fantasy 玩法（积分/预算/动态定价/芯片/转会/联盟）、规则加权预测、社区投票聚合。"
)

UNITS = [
{
    "id": "4.1",
    "title": "SQLAlchemy ORM 基础",
    "concept": [
        "SQLAlchemy 是 Python 最主流的 ORM：用 Python 类映射数据库表，用对象操作替代 SQL 字符串，天然防 SQL 注入。",
        ("h3", "三件套：Engine / Session / Base"),
        ("code", "from sqlalchemy import create_engine\n"
                "from sqlalchemy.orm import sessionmaker, declarative_base\n\n"
                "engine = create_engine(\"sqlite:///cache/f1_app.db\",\n"
                "                       connect_args={\"check_same_thread\": False})\n"
                "SessionLocal = sessionmaker(bind=engine, autoflush=False)\n"
                "Base = declarative_base()",
                "database.py"),
        ("bullet", "Engine：连接池管理（数据库驱动 + 连接复用）。", "Engine"),
        ("bullet", "SessionLocal：会话工厂，每次请求创建独立 Session（事务隔离）。", "SessionLocal"),
        ("bullet", "Base：模型基类，所有表模型继承它；Base.metadata.create_all 建表。", "Base"),
        ("h3", "模型定义示例"),
        ("code", "class User(Base):\n"
                "    __tablename__ = \"users\"\n"
                "    id = Column(Integer, primary_key=True, index=True)\n"
                "    username = Column(String(50), unique=True, nullable=False)\n"
                "    password_hash = Column(String(128), nullable=False)\n"
                "    created_at = Column(DateTime, default=datetime.utcnow)",
                "User 模型"),
    ],
    "qa": [
        ("什么是 ORM？为什么用它？", "ORM（对象关系映射）把表映射为类、行映射为对象，用 Python 语法操作数据库。好处：防 SQL 注入、类型安全、迁移方便、跨数据库（SQLite↔PostgreSQL 切换只需改连接串）。"),
        ("Engine 和 Session 的区别？", "Engine 是底层连接池（全局单例）；Session 是业务工作单元（每请求一个），负责事务。类比：Engine 是数据库连接工厂，Session 是具体一次会话。"),
        ("为什么 SQLite 要加 check_same_thread=False？", "SQLite 默认限制连接只能被创建线程使用。FastAPI 多线程处理请求（默认线程池），跨线程复用连接会报错，需关闭该检查。"),
    ],
},
{
    "id": "4.2",
    "title": "8 张表设计与关系",
    "concept": [
        "项目数据库设计 8 张核心表，覆盖用户体系 + Fantasy 游戏 + 投票。",
        ("table", ["表名", "用途", "关键字段", "关系"], [
            ["users", "用户账号", "id, username, password_hash, chip_* 字段", "1:N fantasy_teams"],
            ["fantasy_teams", "幻想车队（每站一支）", "id, user_id, race_key, budget_used, total_points", "N:1 users"],
            ["fantasy_picks", "车队内车手选择", "id, team_id, driver_code, price, points", "N:1 fantasy_teams"],
            ["race_results", "分站结果缓存", "year, round, driver_code, position, points", "唯一约束 (year,round,driver)"],
            ["driver_standings", "车手积分榜", "year, driver_code, position, points", "唯一约束 (year,driver)"],
            ["votes", "社区投票", "id, user_id, race_key, driver_code", "唯一约束 (user,race)"],
            ["transfers", "转会记录", "id, team_id, driver_in, driver_out, cost", "N:1 fantasy_teams"],
            ["leagues", "联盟", "id, name, invite_code", "N:M users"],
        ], [2.4, 3.2, 5.4, 3.6]),
        ("h3", "relationship 与聚合查询"),
        ("code", "class FantasyTeam(Base):\n"
                "    __tablename__ = \"fantasy_teams\"\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    user_id = Column(Integer, ForeignKey(\"users.id\"))\n"
                "    owner = relationship(\"User\", back_populates=\"teams\")\n"
                "    picks = relationship(\"FantasyPick\", back_populates=\"team\")\n\n"
                "# 聚合查询：每支车队的总积分排行\n"
                "from sqlalchemy import func\n"
                "rows = (db.query(FantasyTeam, func.sum(FantasyPick.points))\n"
                "        .join(FantasyPick)\n"
                "        .group_by(FantasyTeam.id)\n"
                "        .order_by(func.sum(FantasyPick.points).desc())\n"
                "        .all())",
                "关系 + 聚合"),
    ],
    "qa": [
        ("Fantasy 选车手为什么不直接存车手名字？", "存 driver_code（三字码，如 VER）而非中文名：① 数据量小；② 与 Ergast/FastF1 数据源一致，方便 join；③ 展示层用映射表转全名，避免存重复冗余。"),
        ("unique 约束怎么加？用于什么场景？", "Column(unique=True) 或 UniqueConstraint：防止重复数据。如 votes 表 (user_id, race_key) 唯一 → 每人每站只能投一票；race_results (year, round, driver) 唯一 → 结果缓存不重复。"),
    ],
},
{
    "id": "4.3",
    "title": "模型加字段必须迁移",
    "concept": [
        "SQLAlchemy 的 create_all 只在表不存在时建表，不会给已存在的表加新列。开发期改模型后接口会报 no such column 500。",
        ("h3", "自动迁移方案（开发期）"),
        ("code", "def _auto_migrate(engine, Base):\n"
                "    \"\"\"PRAGMA 对比 + ALTER TABLE 自动补列（保留数据）\"\"\"\n"
                "    inspector = inspect(engine)\n"
                "    for table_name, model in Base.metadata.tables.items():\n"
                "        if table_name not in inspector.get_table_names():\n"
                "            continue\n"
                "        existing = {c['name'] for c in inspector.get_columns(table_name)}\n"
                "        for col in model.columns:\n"
                "            if col.name not in existing:\n"
                "                ddl = f\"ALTER TABLE {table_name} ADD COLUMN {col.name} {col.type}\"\n"
                "                engine.execute(text(ddl))\n"
                "                print(f\"[migrate] {table_name}.{col.name} added\")",
                "database.py _auto_migrate"),
        ("bullet", "init_db() 末尾自动调用 _auto_migrate()，保留已有数据。", "自动调用"),
        ("bullet", "曾因 User 新增 chip_* 字段未迁移导致登录 500，已修复并补 4 列——这就是「加字段必须迁移」的实战教训。", "真实事故"),
        ("bullet", "生产环境应升级 Alembic（正规迁移工具）。", "生产方案"),
    ],
    "qa": [
        ("SQLite 的 create_all 为什么不给已有表加列？", "create_all 只执行 CREATE TABLE IF NOT EXISTS，表已存在则跳过。SQLite 的 ALTER TABLE 能力有限（ADD COLUMN 可以，DROP COLUMN 需重建表）。开发期用 PRAGMA 对比 + ALTER TABLE 自动补列。"),
        ("为什么说「模型加字段必须迁移」？", "因为 create_all 不会动已有表。改了模型不迁移，新代码查新列直接报 no such column，接口 500。本项目踩过一次（User 加 chip_* 字段登录 500）。"),
        ("生产环境怎么做迁移？", "用 Alembic：alembic revision 生成迁移脚本 → alembic upgrade head 执行；支持回滚。开发期自动迁移方案只适合单机小项目。"),
    ],
},
{
    "id": "4.4",
    "title": "FastAPI 依赖注入",
    "concept": [
        "依赖注入（DI）：FastAPI 自动解析函数参数中的依赖，把「创建 Session」这类样板代码从业务函数中剥离。",
        ("h3", "get_db 依赖"),
        ("code", "from fastapi import Depends\n\n"
                "def get_db():\n"
                "    db = SessionLocal()\n"
                "    try:\n"
                "        yield db\n"
                "    finally:\n"
                "        db.close()   # 保证会话必被关闭\n\n"
                "@app.get(\"/api/fantasy/teams\")\n"
                "def list_teams(db: Session = Depends(get_db)):\n"
                "    return db.query(FantasyTeam).all()",
                "依赖注入示例"),
        ("bullet", "yield 模式：请求前创建、请求后自动清理（finally 关闭）。", "yield"),
        ("bullet", "同一依赖多处使用只实例化一次（缓存），性能好。", "缓存"),
        ("bullet", "鉴权依赖可组合：get_db + get_current_user 叠加。", "组合"),
    ],
    "qa": [
        ("FastAPI 依赖注入解决了什么问题？", "① 样板代码剥离（每个接口都要建/关 Session）；② 生命周期管理（yield + finally 保证资源释放）；③ 可测试（mock 依赖注入）；④ 组合复用（鉴权依赖叠加）。"),
        ("yield 和 return 依赖的区别？", "yield 支持「请求后清理」：try/finally 中释放资源；return 只提供值。数据库会话必须用 yield，否则连接泄漏。"),
    ],
},
{
    "id": "4.5",
    "title": "配置管理与 Pydantic Settings",
    "concept": [
        "敏感配置（密钥/数据库地址）不硬编码在代码里，通过环境变量或 .env 注入。",
        ("code", "from pydantic_settings import BaseSettings\n\n"
                "class Settings(BaseSettings):\n"
                "    DATABASE_URL: str = \"sqlite:///cache/f1_app.db\"\n"
                "    JWT_SECRET: str = \"change-me\"\n"
                "    JWT_EXPIRE_MINUTES: int = 60 * 24\n\n"
                "    class Config:\n"
                "        env_file = \".env\"   # 从 .env 读取，未设置用默认值\n\n"
                "settings = Settings()",
                "config.py"),
        ("bullet", ".env 加入 .gitignore，防止密钥入库。", "安全"),
        ("bullet", "生产切换 PostgreSQL 只需改 DATABASE_URL，代码零改动。", "可迁移"),
    ],
    "qa": [
        ("密钥为什么不能写死在代码里？", "代码会进 Git 仓库，密钥泄漏 = 安全事件。用环境变量/.env 注入，.env 被 .gitignore 排除，只有部署者持有。"),
        ("Pydantic Settings 相比 os.getenv 的优势？", "① 类型自动转换（int/bool）；② 默认值与必填声明；③ .env 文件自动加载；④ 配置类集中管理、IDE 补全。"),
    ],
},
{
    "id": "4.6",
    "title": "密码安全：bcrypt 哈希",
    "concept": [
        "明文存密码是致命安全错误。本项目用 bcrypt 单程哈希 + 加盐存储，即使数据库泄露也无法还原密码。",
        ("h3", "实现（绕过 passlib 直连 bcrypt）"),
        ("code", "import bcrypt\n\n"
                "def hash_password(plain: str) -> str:\n"
                "    salt = bcrypt.gensalt()\n"
                "    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')\n\n"
                "def verify_password(plain: str, hashed: str) -> bool:\n"
                "    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))",
                "auth 密码工具"),
        ("bullet", "为什么绕过 passlib：passlib 1.7.4 与 bcrypt 4.x 存在兼容性崩溃（AttributeError），直连 bcrypt 更稳定。", "技术决策"),
        ("bullet", "bcrypt 特性：内置随机盐、计算慢（对抗暴力破解）、每次哈希结果不同（验证时 checkpw 重算）。", "原理"),
    ],
    "qa": [
        ("为什么不能用 MD5/SHA 直接存密码？", "MD5/SHA 是快速摘要，可被彩虹表/GPU 暴力破解。bcrypt 设计为「故意慢」+ 自动加盐，相同密码每次哈希不同，暴力破解成本高几个数量级。"),
        ("bcrypt 存的是哈希还是密文？", "哈希。bcrypt 输出格式含版本+盐+哈希（如 $2b$12$...），checkpw 从哈希中提取盐重算比对。单向不可逆，因此密码找回只能重置不能查看。"),
        ("为什么不用 passlib？", "passlib 1.7.4 已多年未更新，与 bcrypt 4.x 的私有 API 变化不兼容，直接调用报 AttributeError。直连 bcrypt 库更可靠，代码也更少。"),
    ],
},
{
    "id": "4.7",
    "title": "JWT 无状态鉴权",
    "concept": [
        "JWT（JSON Web Token）：服务端签发签名 Token，客户端保存并在后续请求携带，服务端验签即可确认身份——无需在服务端存会话，天然适合前后端分离与多实例部署。",
        ("h3", "签发与校验"),
        ("code", "import jwt\n\n"
                "def create_token(user_id: int) -> str:\n"
                "    payload = {\n"
                "        \"sub\": str(user_id),\n"
                "        \"exp\": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),\n"
                "    }\n"
                "    return jwt.encode(payload, settings.JWT_SECRET, algorithm=\"HS256\")\n\n"
                "def get_current_user(\n"
                "        authorization: str = Header(...),\n"
                "        db: Session = Depends(get_db)) -> User:\n"
                "    token = authorization.removeprefix(\"Bearer \")\n"
                "    payload = jwt.decode(token, settings.JWT_SECRET,\n"
                "                          algorithms=[\"HS256\"])   # 过期抛异常\n"
                "    user = db.query(User).get(int(payload[\"sub\"]))\n"
                "    if not user:\n"
                "        raise HTTPException(401, \"用户不存在\")\n"
                "    return user",
                "auth JWT 实现"),
        ("h3", "前端配合"),
        ("bullet", "登录成功 → localStorage 存 token → axios 请求拦截器附加 Authorization: Bearer {token}。", "前端"),
        ("bullet", "受保护接口（Fantasy）在依赖里声明 user: User = Depends(get_current_user)，自动鉴权。", "保护"),
        ("bullet", "JWT 无状态：服务器重启不丢登录态；缺点是 Token 无法主动吊销（除非黑名单）。", "特性"),
    ],
    "pits": [
        ("Bearer 格式", "前端 Header 必须带 Bearer 前缀，后端 removeprefix('Bearer ') 解析；两边不一致会 401。"),
        ("密钥强度", "JWT_SECRET 弱密钥会被爆破伪造 Token，必须用随机长串并在 .env 管理。"),
    ],
    "qa": [
        ("JWT 鉴权流程讲一下？", "登录成功 → 服务端用密钥签发含用户 id 与过期时间的 JWT → 前端存 localStorage → 请求拦截器加 Authorization: Bearer token → 服务端依赖注入 get_current_user 验签解出 user_id → 查库返回用户。"),
        ("JWT 和 Session 鉴权区别？", "Session：服务端存会话、客户端存 session_id，适合单体、可主动注销；JWT：服务端无状态、客户端存完整 token，适合微服务/分布式、无需 session 存储。JWT 缺点是无法主动吊销。"),
        ("JWT 过期了怎么办？", "前端收到 401 → 清除本地 token → 跳登录页重新登录。进阶方案：短期 access token + 长期 refresh token 刷新。"),
    ],
},
{
    "id": "4.8",
    "title": "Fantasy 积分规则与预算校验",
    "concept": [
        "Fantasy（幻想 F1）：用户用预算挑选车手组成车队，按真实比赛积分结算。核心业务规则：预算上限 + 车手价格 + 积分结算。",
        ("h3", "积分规则"),
        ("bullet", "车手积分 = 真实比赛积分（P1=25, P2=18, P3=15 … P10=1）按车队选择计。", "基础积分"),
        ("bullet", "车队预算上限（如 100M），每名车手有市场价，选人总价不得超预算。", "预算"),
        ("bullet", "动态定价：车手价格随热度浮动（base_price × 函数 + trend_bonus - DNF 惩罚）。", "定价"),
        ("h3", "预算校验（服务端必须做）"),
        ("code", "def validate_budget(db, team_id: int, picks: list[str], budget: int = 100):\n"
                "    total = sum(driver_price(db, code) for code in picks)\n"
                "    if total > budget:\n"
                "        raise HTTPException(400, f\"超出预算 {total}/{budget}\")\n"
                "    return total",
                "预算校验"),
        ("bullet", "前端校验只是体验优化，服务端校验才是安全底线（防绕过前端直接调 API）。", "双端校验"),
    ],
    "qa": [
        ("Fantasy 预算校验为什么前端做了后端还要做？", "前端校验只防正常用户误操作；恶意用户可绕过前端直接调 API。所有资金/配额类规则必须服务端强制校验，否则可被刷。"),
        ("动态定价怎么设计？", "基准价（按上赛季表现/市场价）+ 趋势加成（被选率上升则涨价）+ 惩罚（DNF 掉价），公式示例：price = base × (1 + k1×popularity - k2×dnf_rate)，可调参数保证价格波动有界。"),
    ],
},
{
    "id": "4.9",
    "title": "Fantasy 扩展：芯片 / 转会 / 联盟",
    "concept": [
        "为提升玩法深度，Fantasy 加入三个扩展系统。",
        ("table", ["系统", "玩法", "技术要点"], [
            ["芯片系统", "Limitless（无限预算卡）/ Wildcard（小丑卡翻倍）/ No Negative（保底 0 分）", "users 表加 chip_* 字段；每站每类芯片限用一次"],
            ["转会市场", "比赛周内可用积分换车手", "transfers 表记录 in/out/cost；结算时校验合法性"],
            ["联盟系统", "创建联盟 + 邀请码加入，联盟内排行", "invite_code = secrets.token_urlsafe(6)；outerjoin 排行榜"],
        ], [2.2, 6.4, 6.0]),
        ("h3", "联盟邀请码"),
        ("code", "import secrets\n"
                "invite_code = secrets.token_urlsafe(6)   # 安全随机，不可预测\n\n"
                "# 排行榜：联盟成员按总分排行\n"
                "rows = (db.query(User, func.sum(FantasyTeam.total_points))\n"
                "        .join(FantasyTeam, FantasyTeam.user_id == User.id)\n"
                "        .join(LeagueMember, LeagueMember.user_id == User.id)\n"
                "        .filter(LeagueMember.league_id == league.id)\n"
                "        .group_by(User.id)\n"
                "        .order_by(func.sum(FantasyTeam.total_points).desc())\n"
                "        .all())",
                "联盟实现"),
        ("bullet", "邀请码必须用 secrets 模块（密码学安全），不能用 random（可预测）。", "安全"),
        ("bullet", "芯片字段的迁移：users 表加 chip_* 4 列（触发过 no such column 500 事故）。", "迁移教训"),
    ],
    "qa": [
        ("联盟邀请码为什么要用 secrets 而不是 random？", "random 是伪随机数生成器，种子可预测，攻击者能枚举出他人邀请码随意加入联盟；secrets 使用操作系统熵源，密码学安全。"),
        ("芯片系统的数据模型怎么设计？", "两个方案：① 每类芯片一个字段（limitless_used 等）——简单直观；② 独立表 chip_usage(user, race, type)——灵活可扩展。本项目用方案①（开发快），字段加在 users 表。"),
    ],
},
{
    "id": "4.10",
    "title": "规则加权预测（rule_v1）与社区投票",
    "concept": [
        "AI 预测模块的初版：用领域规则加权评分预测获胜概率；社区投票则是让用户投票 + 聚合展示。二者是 XGBoost（阶段 4）之前的能力铺垫。",
        ("h3", "rule_v1 规则模型"),
        ("bullet", "特征：近 5 场表现、排位赛位置、车队强弱、赛道历史、轮胎策略倾向。", "特征"),
        ("bullet", "加权求和：表现分 = w1×近5场均分 + w2×排位分 + w3×车队分…，权重人工设定。", "加权"),
        ("bullet", "softmax 归一化 → 每人获胜概率。", "归一化"),
        ("bullet", "XGBoost 上线后 rule_v1 保留为 fallback（模型不存在/排位赛不可用时降级）。", "降级"),
        ("h3", "社区投票聚合"),
        ("bullet", "投票限制：只能投「进行中」的分站，每人每站一票（唯一约束）。", "限制"),
        ("bullet", "聚合：按车手分组 count，返回票数占比条形图。", "聚合"),
        ("bullet", "页面下方展示上一场结果作为投票参考。", "参考"),
    ],
    "qa": [
        ("规则加权模型的优缺点？", "优点：可解释（权重即业务规则）、无需训练数据、冷启动快；缺点：权重靠拍脑袋、无法捕捉复杂非线性关系、准确率天花板低（本项目 Top-1 33.33%）。因此升级 XGBoost（41.67%）。"),
        ("为什么预测结果要做 softmax 归一化？", "各车手得分量纲不一致（近 5 场分 vs 排位名次），softmax 把得分转成和为 1 的概率分布，语义清晰（获胜概率），也便于展示百分比。"),
    ],
},
{
    "id": "4.11",
    "title": "阶段 3 综合面试问答",
    "qa": [
        ("完整讲一下用户登录到 Fantasy 的鉴权链路？", "注册（bcrypt 哈希）→ 登录（验证密码，签发 JWT）→ 前端存 token → 请求拦截器加 Bearer → 后端 get_current_user 依赖验签 → Fantasy 接口声明依赖自动鉴权 → 校验预算/芯片规则 → 写库返回。"),
        ("数据库设计时怎么考虑扩展性？", "① 预留枚举/状态字段（如芯片类型）；② 唯一约束防重复；③ 外键+索引保一致性；④ 查询频率高的表（积分榜）可加缓存；⑤ SQLite→PostgreSQL 迁移只改连接串。"),
        ("讲一个你处理过的数据库 Bug？", "User 表新增 chip_* 字段后未迁移，create_all 不会给已有表加列，登录接口查新字段报 no such column 500。修复：实现 _auto_migrate（PRAGMA 对比 + ALTER TABLE 补列），并沉淀「模型加字段必须迁移」规范。"),
        ("JWT_SECRET 泄漏会怎样？怎么防？", "攻击者可伪造任意用户 Token 登录。防：① 强随机长密钥；② .env 管理不入库；③ 定期轮换；④ 关键操作二次校验。"),
    ],
},
]
