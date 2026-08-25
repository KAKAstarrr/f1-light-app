# -*- coding: utf-8 -*-
"""第七部分：数据科学基础 + 第八部分：Streamlit 原型"""

DS_INTRO = (
    "本部分为数据科学三件套（NumPy / Pandas / Matplotlib）知识点与 Streamlit 快速原型开发知识点，"
    "面向数据分析师与全栈岗位：既有数据处理技巧，也有「用 Streamlit 一天出 MVP 看板」的工程实践。"
)

UNITS = [
# ============ 数据科学 ============
{
    "id": "6.1",
    "title": "NumPy：ndarray 核心",
    "concept": [
        "NumPy 是 Python 数值计算基础库，核心是 n 维数组 ndarray（同质、连续内存、向量化计算，比 Python list 快 1-2 个数量级）。",
        ("h3", "高频操作"),
        ("code", "import numpy as np\n\n"
                "arr = np.array([1, 2, 3, 4])        # 创建\n"
                "arr * 2                              # 向量化：无循环\n"
                "np.arange(0, 100, 0.5)               # 等距序列（采样网格）\n"
                "np.interp(grid, x, y)                # 线性插值（B4 重采样）\n"
                "np.nan_to_num(a, nan=0.0)            # NaN 清洗\n"
                "a.astype(float)                      # 类型转换（numpy -> python 需 .item()）\n"
                "np.where(cond, x, y)                 # 条件选择",
                "NumPy 高频"),
        ("bullet", "向量化：用数组运算替代 Python 循环，性能提升的关键。", "向量化"),
        ("bullet", "广播（broadcasting）：形状不同的数组自动对齐运算（如 数组 + 标量）。", "广播"),
    ],
    "qa": [
        ("NumPy 数组比 Python list 快在哪里？", "① 同质类型连续内存（list 是对象指针数组，缓存不友好）；② 向量化运算用 C 实现（无 Python 循环解释开销）；③ SIMD 指令优化。"),
        ("np.interp 的作用？项目中哪里用到？", "一维线性插值：给定新 x 网格，在已知 (x, y) 上求 y 值。B4 速度叠加用它把不同车手速度重采样到 50m 统一网格。"),
    ],
},
{
    "id": "6.2",
    "title": "Pandas：筛选 / groupby / 时间转换",
    "concept": [
        "Pandas 是数据分析核心库：DataFrame 二维表 + 丰富的数据操作 API。F1 圈速/遥测/赛果都是 DataFrame 形态。",
        ("h3", "高频三板斧"),
        ("code", "import pandas as pd\n\n"
                "# 筛选：布尔索引\n"
                "dry = laps[laps['Compound'] != 'WET']\n"
                "top10 = results[results['Position'] <= 10]\n\n"
                "# 分组聚合\n"
                "laps.groupby('Driver')['LapTime'].min()          # 每人最快\n"
                "laps.groupby(['Driver','Stint']).size()          # 每段圈数\n\n"
                "# 时间转换\n"
                "laps['LapTime'].dt.total_seconds()               # timedelta -> 秒\n"
                "pd.to_datetime(races['date'])                    # 字符串 -> 时间\n\n"
                "# 排序\n"
                "laps.sort_values('LapTime').head(5)",
                "Pandas 高频"),
        ("bullet", "布尔索引：df[条件] 返回满足条件的行，条件用 & | ~ 组合（不能用 and/or）。", "筛选"),
        ("bullet", "groupby 返回分组对象，配合 agg/apply/transform 使用。", "分组"),
        ("bullet", "dt 访问器：时间列专用（total_seconds/normalize/dayofweek）。", "时间"),
    ],
    "pits": [
        ("and/or 报错", "DataFrame 布尔条件组合必须用 & | ~，用 Python 的 and/or 会报「truth value is ambiguous」——Pandas 高频坑。"),
    ],
    "qa": [
        ("Pandas 筛选和 groupby 的典型用法？", "筛选用布尔索引（laps[laps['Compound']!='WET']）；分组用 groupby+agg（最快圈、每段圈数、Stint 策略重建）。数据分析 80% 时间在做这两件事。"),
        ("timedelta 怎么转成秒？", "df['col'].dt.total_seconds()（Series 方法）或单个值 .total_seconds()。转换后还需注意 NaN 处理（缺失圈速）。"),
        ("groupby 后想保留原表行怎么用 transform？", "groupby.agg 会压缩行数；transform 保持行数不变（如每人圈速减去其最快圈得相对差距）。"),
    ],
},
{
    "id": "6.3",
    "title": "Matplotlib：中文与样式配置",
    "concept": [
        "Matplotlib 是 Python 基础绘图库。中文显示是必经坑：默认字体不含中文字形，需配置。",
        ("h3", "中文配置模板"),
        ("code", "import matplotlib.pyplot as plt\n"
                "plt.rcParams['font.sans-serif'] = ['SimHei']      # 黑体支持中文\n"
                "plt.rcParams['axes.unicode_minus'] = False        # 负号正常显示\n\n"
                "fig, ax = plt.subplots(figsize=(10, 6))\n"
                "ax.plot(x, y, label='速度')\n"
                "ax.set_title('圈速对比')\n"
                "ax.legend()\n"
                "plt.savefig('chart.png', dpi=150)\n"
                "plt.close(fig)                                    # 释放内存",
                "Matplotlib 模板"),
        ("bullet", "axes.unicode_minus=False：否则负号显示为方块。", "负号坑"),
        ("bullet", "批量绘图后 plt.close(fig) 防内存泄漏（FastAPI 里尤其重要）。", "内存"),
    ],
    "qa": [
        ("Matplotlib 中文乱码怎么解决？", "设置 rcParams['font.sans-serif']=['SimHei']（指定支持中文的字体）并设 axes.unicode_minus=False 修复负号方块。也可用 plt.rcParams['font.family'] 全局指定。"),
        ("在 Web 服务里画图要注意什么？", "① 用 Agg 后端（无界面环境）；② plt.close(fig) 释放内存；③ 保存到临时文件或 BytesIO 返回；④ 中文配置每次进程生效一次即可。"),
    ],
},
{
    "id": "6.4",
    "title": "数据科学综合面试问答",
    "qa": [
        ("数据分析的完整流程是什么？结合 F1 项目讲。", "① 明确问题（谁在哪个弯道最快）；② 数据获取（FastF1 拉遥测）；③ 清洗（NaN/进出站圈/采样）；④ 分析（网格对齐、Delta 积分、分组统计）；⑤ 可视化（ECharts/Matplotlib）；⑥ 结论与产品化（页面展示）。"),
        ("如何处理缺失值？", "① 理解缺失原因（DNF 无圈速=业务性缺失，不该填充）；② 数值型可填充均值/中位数或插值；③ 类别型填充众数；④ 缺失率高的列直接删除；⑤ 决策树/XGBoost 原生支持缺失。"),
        ("数据分析师如何用 SQL 和 Pandas 结合工作？", "大表用 SQL 聚合（GROUP BY/窗口函数）减少传输，小结果集用 Pandas 精加工（透视、时序、可视化）。F1 项目数据在 API/CSV，故主要用 Pandas。"),
    ],
},

# ============ Streamlit ============
{
    "id": "7.1",
    "title": "Streamlit 快速原型开发",
    "concept": [
        "Streamlit 是「纯 Python 出 Web 看板」的框架：写 Python 脚本即应用，交互组件自动渲染，无需 HTML/JS。本项目用它做数据看板 MVP，验证数据管道后再上 Vue3 正式版。",
        ("h3", "页面配置与布局"),
        ("code", "import streamlit as st\n\n"
                "st.set_page_config(\n"
                "    page_title=\"F1 数据看板\",\n"
                "    page_icon=\"🏎️\",\n"
                "    layout=\"wide\",          # 宽屏布局\n"
                ")\n\n"
                "st.title(\"F1 2025 赛季数据\")\n"
                "col1, col2, col3 = st.columns(3)   # 三列布局\n"
                "col1.metric(\"车手冠军\", \"VER\", \"+12\")\n"
                "col2.metric(\"分站数\", \"24\", None)",
                "Streamlit 布局"),
        ("bullet", "st.metric：指标卡（数值+增量对比）。", "指标"),
        ("bullet", "st.columns / st.sidebar：布局与侧边栏。", "布局"),
    ],
    "qa": [
        ("Streamlit 的核心机制是什么？", "脚本自上而下执行 + 组件状态触发 rerun：任何交互（按钮/下拉）都重跑整个脚本，组件记住状态。因此「数据加载」必须放缓存装饰器，否则每次交互重复拉数据。"),
        ("Streamlit 和 Vue3 怎么选型？", "原型期（验证数据、快速迭代）用 Streamlit：1 天出 MVP、纯 Python；正式产品（交互复杂、多页面、品牌化）用 Vue3。本项目两者结合：Streamlit 验证 → Vue3 正式。"),
    ],
},
{
    "id": "7.2",
    "title": "数据展示与小部件",
    "concept": [
        ("h3", "展示组件"),
        ("code", "st.dataframe(df, use_container_width=True)   # 可交互表格\n"
                "st.table(df.head(5))                        # 静态表格\n"
                "st.line_chart(df[['speed']])                # 快速折线\n"
                "st.bar_chart(df.groupby('Driver')['pts'].sum())",
                "数据展示"),
        ("h3", "交互小部件"),
        ("code", "year = st.selectbox(\"选择年份\", [2026, 2025, 2024, 2023], index=1)\n"
                "drivers = st.multiselect(\"车手\", all_drivers, default=['VER', 'NOR'])\n"
                "with st.sidebar:\n"
                "    rnd = st.slider(\"分站\", 1, 24, 1)",
                "小部件"),
        ("bullet", "selectbox/multiselect/slider 返回值即当前选中值，rerun 后保持。", "状态"),
        ("bullet", "st.cache_data：数据加载函数加装饰器，参数相同则跳过重算（TTL 可配）。", "缓存"),
    ],
    "qa": [
        ("st.cache_data 和 st.cache_resource 的区别？", "cache_data 缓存序列化数据（DataFrame/JSON，磁盘+内存）；cache_resource 缓存不可序列化资源（数据库连接、模型实例，仅内存）。API 结果用 cache_data，FastF1 模型用 cache_resource。"),
        ("Streamlit 怎么调用后端接口？", "直接 requests 调 FastAPI（本项目 streamlit_app.py 调 /api 接口）；或内嵌 Python 函数直连 data_source。原型期常直接调用数据源层函数，省去 HTTP 层。"),
    ],
},
{
    "id": "7.3",
    "title": "Streamlit 综合面试问答",
    "qa": [
        ("讲一下你用 Streamlit 做了什么？", "用纯 Python 搭了 F1 数据看板 MVP：赛程/结果/积分榜/圈速/轮胎策略页面，验证了 FastF1 数据管道与可视化方案，为正式 Vue3 前端提供产品原型。"),
        ("Streamlit 的局限？什么时候不用它？", "① 复杂交互受限（拖拽、自定义组件少）；② 多页面与路由弱；③ 性能（整脚本 rerun）；④ 品牌化 UI 难。正式产品、强交互场景改用 Vue3。"),
    ],
},
]
