# -*- coding: utf-8 -*-
"""第六部分：阶段 4 XGBoost AI 预测（5 个阶段完整知识点）"""

PART4_INTRO = (
    "本部分对应项目「阶段 4：AI 预测 XGBoost 迁移」全部知识点，按 5 个阶段组织："
    "① 数据采集 ② 特征工程 ③ 模型训练 ④ 在线推理 ⑤ SHAP 解释。"
    "核心成果：XGBoost 模型 Top-1 命中率 41.67%（规则模型 33.33%），4/5 指标全面领先。"
)

UNITS = [
{
    "id": "5.1",
    "title": "阶段 1：数据采集与数据集构建",
    "concept": [
        "机器学习第一步是拿到干净、完整、有标签的数据。本项目采集 2018-2025 共 173 场比赛、3458 行训练数据。",
        ("h3", "采集方案"),
        ("bullet", "数据源：Ergast API（赛果/积分榜/赛道），复用 cache/ergast_cache/（1 小时 TTL）避免重复请求。", "数据源"),
        ("bullet", "采集脚本：scripts/collect_training_data.py，0.5s 间隔 + 3 次重试处理 429 限流。", "限流"),
        ("bullet", "产出：races_2018_2025.csv（29 列）+ standings_2018_2025.csv + circuits.csv。", "产出"),
        ("h3", "数据质量"),
        ("table", ["维度", "数值", "含义"], [
            ["车手数", "43", "2018-2025 全量参赛车手"],
            ["缺失值", "无", "清洗彻底"],
            ["胜负比", "1:19", "获胜是稀有事件 → 类别不平衡"],
            ["DNF 率", "11%", "退赛概率建模有意义"],
            ["胜者分布", "VER 68 / HAM 43 / NOR 11", "头部车手集中"],
        ], [2.6, 4.0, 8.0]),
        ("h3", "为什么数据要够「宽」"),
        ("bullet", "29 列 = 赛果 + 排位 + 积分榜 + 赛道 + 车手历史统计，特征宽度决定模型信息上限。", "宽度"),
        ("bullet", "8 年跨度覆盖技术规则更迭（2022 地效时代），模型见过多种规则环境，泛化更好。", "跨度"),
    ],
    "qa": [
        ("训练数据从哪里来？怎么保证质量？", "Ergast API 采集 2018-2025 历史赛果，脚本自动重试+缓存。质量保证：去重、缺失检查、异常值清洗（如取消的雨战）、标签与特征时间对齐（防泄漏）。"),
        ("为什么收集 8 年的数据？", "F1 规则每 5 年左右大改（2022 地效、2026 新引擎），只有覆盖多代规则才能让模型学到「通用的获胜规律」而非特定时代的过拟合。"),
    ],
},
{
    "id": "5.2",
    "title": "阶段 2：特征工程（19 特征 6 组）",
    "concept": [
        "特征工程是把原始赛果转成模型可学习的信号。本项目构造 19 个特征，分 6 组，核心纪律是「防数据泄漏」——只能用比赛开始前已知的信息。",
        ("h3", "19 特征 6 组结构"),
        ("table", ["组", "特征示例", "含义"], [
            ["车手历史表现", "近5场均分、近期胜率、上赛季总积分", "个体长期/短期状态"],
            ["排位赛信号", "排位名次、排位得分", "单圈能力（赛前已知）"],
            ["车队强度", "车队积分、车队近5场均分", "赛车性能底盘"],
            ["赛道历史", "该赛道历史胜率、平均名次", "车手-赛道适配"],
            ["积分榜位置", "当前积分、积分榜名次", "赛季走势"],
            ["天气/环境", "（预留）天气、轮胎", "环境因素"],
        ], [3.2, 5.2, 6.0]),
        ("h3", "防泄漏：shift + cumsum"),
        ("code", "# 关键：只用截止上一场的累计数据，绝不用本场结果\n"
                "df['prev_points'] = df.groupby('driver')['points'].shift(1)\n"
                "df['season_points'] = df.groupby('driver')['points'].cumsum().shift(1)\n"
                "df['form_5'] = df.groupby('driver')['points'].rolling(5).mean().shift(1)\n\n"
                "# shift(1)：去掉当前行 → 特征里不含本场结果\n"
                "# cumsum().shift(1)：赛季累计积分，但截止上一场",
                "shift+cumsum 防泄漏"),
        ("bullet", "shift(1) 让每行特征 = 截止上一场的状态，本场结果是 label，不参与特征。", "shift"),
        ("bullet", "rolling(5).mean() 滑动均值需要先 shift 再算（组内先排时间序）。", "rolling"),
        ("bullet", "验证：特征与 label 同源于「上一场」，训练/预测时保持一致。", "一致性"),
    ],
    "pits": [
        ("数据泄漏", "若直接用本场排位/本场积分做特征，模型在训练集表现虚高、线上预测完全失效——泄漏是 ML 最隐蔽的错误，本项目用 shift 严格隔离。"),
    ],
    "qa": [
        ("什么是数据泄漏？举例说明。", "特征里包含了「预测目标的信息」。例：预测正赛冠军却用正赛积分做特征——训练时模型「偷看答案」。本项目用 shift(1) 保证特征截止上一场，本场只做 label。"),
        ("shift(1) 和 rolling 怎么配合？", "先 groupby(driver) 保证同一车手内滑动，再 rolling(5).mean() 取近 5 场均值，最后 shift(1) 排除当前场。顺序错乱（先 shift 再 rolling）会把窗口错位。"),
        ("19 个特征怎么来的？", "从 6 个业务维度设计（个体状态/排位/车队/赛道/赛季/环境），每个维度取 2-4 个可计算的统计量，共 19 个。特征数量与数据量匹配（3458 行 ≈ 19×180，避免维数灾难）。"),
    ],
},
{
    "id": "5.3",
    "title": "阶段 3：XGBoost 模型训练",
    "concept": [
        "XGBoost（eXtreme Gradient Boosting）是梯度提升树集成算法：串行训练多棵决策树，每棵树学习前面所有树的残差，最终加权投票。Kaggle 表格数据竞赛的常胜将军。",
        ("h3", "训练配置"),
        ("code", "import xgboost as xgb\n\n"
                "model = xgb.XGBClassifier(\n"
                "    max_depth=4,           # 树深：防过拟合（特征仅 19 个）\n"
                "    n_estimators=150,      # 树数量\n"
                "    learning_rate=0.1,\n"
                "    scale_pos_weight=19,   # 正负样本比 1:19 → 惩罚多数类\n"
                "    eval_metric='logloss',\n"
                "    random_state=42,\n"
                ")\n"
                "model.fit(X_train, y_train)\n"
                "model.save_model('ml/models/xgb_v1.json')",
                "train_xgboost.py"),
        ("bullet", "max_depth=4：特征少，浅树足够表达，深了过拟合。", "防过拟合"),
        ("bullet", "scale_pos_weight=19：正类（获胜）稀有，给正类 19 倍权重，模型不再「全猜输」。", "不平衡处理"),
        ("bullet", "eval_metric='logloss'：概率预测任务的恰当指标（Brier 系）。", "评估"),
        ("h3", "评估结果对比"),
        ("table", ["指标", "XGBoost", "rule_v1"], [
            ["Top-1 命中率", "41.67%", "33.33%"],
            ["Log Loss", "0.79", "1.05"],
            ["Brier Score", "0.085", "0.12"],
            ["NDCG@3", "0.71", "0.62"],
            ["平均 Top-1 赔率回报", "更优", "基准"],
        ], [4.4, 4.4, 4.4]),
    ],
    "qa": [
        ("XGBoost 的原理是什么？一句话讲清。", "梯度提升树：第一棵树直接学目标，后面的每棵树学习「前面所有树的残差（梯度方向）」，串行叠加，最终每棵树都是对误差的修正，集成后精度高且自带正则防过拟合。"),
        ("为什么用 XGBoost 而不是深度学习？", "① 表格数据（19 特征 × 3458 行）规模小，树模型表现通常优于 DNN；② 可解释（feature importance/SHAP）；③ 训练快、无需 GPU；④ 自带缺失值处理与正则。"),
        ("scale_pos_weight 是什么？为什么设 19？", "类别不平衡参数：正类（获胜）约 1/20，设为正负样本比 19，让模型把获胜错误看得更重，提升少数类召回。设太大则模型过度预测胜者，需结合评估指标调优。"),
        ("怎么判断模型过拟合/欠拟合？", "训练集 Log Loss 远低于验证集 → 过拟合（降深度/加正则/增数据）；两者都高 → 欠拟合（加深/加树）。本项目训练与验证差距小，且规则性先验（特征有业务含义）增强泛化。"),
    ],
},
{
    "id": "5.4",
    "title": "时间序列交叉验证",
    "concept": [
        "普通 K-Fold 随机打乱会「未来数据训练、过去数据预测」，时间序列必须按时间顺序切分：只允许用过去预测未来。",
        ("code", "# 按年份切分：前 N 年训练，后 1 年验证（滚动前进）\n"
                "for val_year in [2023, 2024, 2025]:\n"
                "    train = df[df['year'] < val_year]\n"
                "    valid = df[df['year'] == val_year]\n"
                "    model = xgb.XGBClassifier(...)\n"
                "    model.fit(X(train), y(train))\n"
                "    score = evaluate(model, X(valid), y(valid))",
                "时间序列 CV"),
        ("bullet", "滚动窗口：逐年后移，模拟真实「预测下一场」场景。", "滚动"),
        ("bullet", "与 K-Fold 区别：K-Fold 随机切，时间序必须保留时序（禁止未来信息）。", "关键区别"),
    ],
    "qa": [
        ("为什么时间序列数据不能用普通 K-Fold？", "K-Fold 随机打乱会让验证集含「早于训练集」的数据，等于用未来预测过去，评估虚高且不真实。时间序列必须按时间切：训练集永远早于验证集。"),
        ("滚动窗口验证具体怎么做？", "以年为单位滚动：{2018-2022 训练, 2023 验证} → {2018-2023 训练, 2024 验证} → {2018-2024 训练, 2025 验证}，每个窗口独立训练评估，取平均。"),
    ],
},
{
    "id": "5.5",
    "title": "阶段 4：在线推理与降级策略",
    "concept": [
        "训练好的模型要服务线上预测：封装成 prediction_service，提供「懒加载单例 + 特征构建 + 概率输出 + 异常降级」。",
        ("h3", "prediction_service 核心设计"),
        ("code", "class PredictionService:\n"
                "    _model = None          # 懒加载单例\n"
                "    _features = None       # 特征列名（顺序必须与训练一致）\n\n"
                "    @classmethod\n"
                "    def get_model(cls):\n"
                "        if cls._model is None:\n"
                "            cls._model = xgb.XGBClassifier()\n"
                "            cls._model.load_model('ml/models/xgb_v1.json')\n"
                "            cls._features = list(pd.read_csv('ml/data/features_train.csv').columns)\n"
                "        return cls._model\n\n"
                "    def predict_race(self, year: int, rnd: int):\n"
                "        df = self._build_xgb_features(year, rnd)   # 从 Ergast+CSV 构建 19 特征\n"
                "        proba = self.get_model().predict_proba(df)[:, 1]\n"
                "        probs = softmax(proba)                     # 归一化成概率分布\n"
                "        return [{'driver': d, 'prob': round(p, 4)}\n"
                "                for d, p in zip(df['driver'], probs)]",
                "prediction_service.py"),
        ("h3", "降级链"),
        ("bullet", "正常：XGBoost 模型在线预测 + SHAP 解释。", "一级"),
        ("bullet", "模型文件不存在 / 排位赛数据不可用（预测依赖排位特征）→ 降级 rule_v1 规则模型。", "二级"),
        ("bullet", "接口异常兜底 {code:500} → 前端展示「预测暂不可用」。", "三级"),
        ("bullet", "懒加载单例：首次请求加载模型，之后复用，避免每次预测都读文件。", "性能"),
    ],
    "qa": [
        ("为什么模型要懒加载单例？", "模型文件加载 + 特征列读取是重操作（几十 MB），每次预测都加载会拖垮接口。首次请求时加载一次，进程内复用；服务多实例部署时各实例各持一份。"),
        ("在线预测和训练时的特征构建有什么一致性要求？", "列名与顺序必须完全一致：预测时用同一份 feature_engineering 逻辑 + 训练时的列名快照（features_train.csv 的 columns）。漏列/错序会让 predict_proba 静默出错。"),
        ("降级策略怎么设计？", "按依赖可用性分级：XGBoost 可用用 XGBoost；模型缺失但规则可用（排位赛数据在）用 rule_v1；全部不可用返回 {code:500}。保证任何情况接口都有响应，前端永不白屏。"),
    ],
},
{
    "id": "5.6",
    "title": "阶段 5：SHAP 特征解释",
    "concept": [
        "SHAP（SHapley Additive exPlanations）基于博弈论 Shapley 值，量化每个特征对预测的贡献，让「黑盒」XGBoost 可解释——这是 AI 落地与面试的加分项。",
        ("h3", "实现"),
        ("code", "import shap\n\n"
                "explainer = shap.TreeExplainer(model)   # 树模型专用，快\n"
                "shap_values = explainer.shap_values(X_row)\n\n"
                "# 对每位车手返回 top-3 贡献特征\n"
                "def top_shap(driver_row, shap_row, top_n=3):\n"
                "    pairs = sorted(zip(feature_names, shap_row),\n"
                "                   key=lambda p: abs(p[1]), reverse=True)\n"
                "    return [{'feature': f, 'value': round(v, 4)}\n"
                "            for f, v in pairs[:top_n]]",
                "SHAP 解释"),
        ("bullet", "TreeExplainer：为树模型定制的高效算法（比 KernelExplainer 快几个数量级）。", "TreeExplainer"),
        ("bullet", "正值 = 推动获胜概率上升；负值 = 拉低；绝对值越大影响越大。", "符号含义"),
        ("bullet", "前端渲染 SHAP 条形图（每个特征的贡献值正负条形）。", "可视化"),
        ("bullet", "懒加载：explainer 也按需创建，避免冷启动开销。", "性能"),
    ],
    "qa": [
        ("SHAP 值是什么？怎么理解正负？", "SHAP 基于 Shapley 值：把预测值分配到各特征，sum 恰好等于预测偏差。正 SHAP 推高预测、负 SHAP 拉低，绝对值 = 影响大小。模型可解释性的行业标准。"),
        ("为什么选 TreeExplainer？", "KernelExplainer 对每个样本要多次重跑模型，极慢；TreeExplainer 利用树结构一次性精确计算所有样本的 SHAP 值，快几个数量级且结果更准（无近似采样误差）。"),
        ("SHAP 在业务上怎么用？", "给用户解释「为什么预测 VER 夺冠」：因为近 5 场均分 + 排位 P1 + 车队积分榜第 1 是最大正向贡献。可解释性提升信任，也是 AI 合规（如金融风控）的硬性要求。"),
    ],
},
{
    "id": "5.7",
    "title": "阶段 4 综合面试问答",
    "qa": [
        ("完整讲一下这个 AI 预测系统的架构？", "数据层：Ergast 采集 2018-2025（173 场 3458 行）→ 特征工程（19 特征 6 组，shift 防泄漏）→ XGBoost 训练（scale_pos_weight=19，时间序 CV）→ 模型存 JSON；服务层：prediction_service 懒加载单例 + 在线特征构建 + softmax 概率 + SHAP 解释 + rule_v1 降级；展示层：前端预测页 + SHAP 条形图。"),
        ("模型准确率 41.67% 说明什么？", "F1 冠军预测本身难（20 车手随机猜 5%），41.67% 远超随机和规则模型（33.33%），说明特征与模型有效。但仍有 58% 猜错——F1 高不确定性（事故/天气/机械故障）是客观上限。"),
        ("如果你的模型线上表现不如训练时，怎么排查？", "① 数据漂移：特征分布变了（规则大改/新车队）；② 特征构建不一致（列名/顺序）；③ 采样偏差；④ 过拟合。对策：监控特征分布 + 定期重训 + 保留 fallback。"),
        ("预测类产品如何评估与迭代？", "离线指标（Log Loss/Brier/Top-1/NDCG）+ 线上反馈（用户对预测结果的打分）+ 赛季复盘（每场命中率）。迭代：加特征 → 调参 → 换模型 → 加解释，每步用评估集回归。"),
    ],
},
]
