# 🏎️ Streamlit 速查手册（F1 Insight Hub）
适用于 `backend/streamlit_app.py`，与 FastAPI 联调使用

## 📂 文件位置与运行
| 项目 | 说明 |
| ---- | ---- |
| 文件名 | `streamlit_app.py` |
| 位置 | `backend/` 目录（与 `main.py` 同级） |
| 启动命令 | `streamlit run streamlit_app.py` |
| 停止服务 | `Ctrl + C` |

---

## 1️⃣ 页面基础（Page Setup）
> ⚠️ `set_page_config` 必须放在所有代码最前面（`import` 之后第一行）
```python
import streamlit as st

st.set_page_config(
    page_title="F1 Insight Hub",  # 浏览器标签标题
    page_icon="🏎️",               # 页面图标
    layout="wide"                 # 宽屏模式（默认窄屏居中）
)

# 文本层级
st.title("F1 数据可视化看板")
st.header("2023 意大利大奖赛")
st.subheader("维斯塔潘圈速分析")
st.write("这是一段普通的文本描述。")
```

---

## 2️⃣ 数据展示（Data Display）
```python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    "Lap": range(1, 6),
    "Driver": ["VER", "VER", "VER", "VER", "VER"],
    "Time": [90.1, 89.8, 90.5, 89.9, 89.7]
})
```
```python
# ✅ 交互式表格（推荐，支持排序、滚动）
st.dataframe(df)

# ❌ 静态表格（仅适合少量数据展示，无法交互）
st.table(df)

# ✅ 指标卡片（适合预测数据、成绩展示）
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="AI 预测胜率", value="45.8%", delta="2.3%")
with col2:
    st.metric(label="最快圈速", value="1:23.456")
with col3:
    st.metric(label="当前排名", value="1st")

# ✅ Debug 工具：格式化展示JSON原始接口数据
st.json({"status": "success", "data": [1, 2, 3]})
```

---

## 3️⃣ 图表绘制（Charts）
> ✅ 优先使用 Streamlit 原生图表
> ❌ 无特殊自定义需求，尽量不用 `st.pyplot`

```python
# 单条折线
st.line_chart(df.set_index("Lap")["Time"])

# 柱状图
st.bar_chart(df.set_index("Lap")["Time"])

# 多车手对比折线图
df_compare = pd.DataFrame(
    np.random.randn(20, 2),
    columns=["VER", "HAM"]
)
st.line_chart(df_compare)
```

---

## 4️⃣ 交互组件（Widgets）
```python
# ✅ 下拉单选框
driver = st.selectbox(
    "选择车手:",
    options=["VER", "HAM", "LEC", "NOR"],
    index=0,
    key="driver_select"
)
st.write(f"你选择了: {driver}")

# ✅ 多选框（多车手对比分析）
drivers = st.multiselect(
    "选择对比车手:",
    ["VER", "HAM", "LEC", "NOR"],
    default=["VER", "HAM"],
    key="driver_multi"
)

# ✅ 功能按钮
if st.button("🔄 刷新数据", key="refresh_btn"):
    st.success("数据已刷新！")
    # st.experimental_rerun() 页面重载

# ✅ 侧边栏（推荐存放全局筛选条件）
st.sidebar.header("过滤器")
year = st.sidebar.slider("选择年份", 2018, 2024, 2023)
round_num = st.sidebar.number_input("选择分站", 1, 24, 1)
```

---

## 5️⃣ 状态与缓存（Cache）
> ⚠️ 只缓存**不会频繁变动的数据**：历史赛季、赛道列表、静态资料
```python
@st.cache_data
def load_static_data():
    # 模拟耗时加载静态数据
    df = pd.DataFrame({"Year": [2023, 2024]})
    return df

seasons_df = load_static_data()
st.dataframe(seasons_df)
```

---

## 6️⃣ 调用 FastAPI（核心联调逻辑）
```python
import requests

API_BASE_URL = "http://localhost:8000"

if st.button("获取最快圈"):
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/fastest-lap",
            params={"driver": "VER"}
        )
        response.raise_for_status()
        data = response.json()

        st.json(data)
        # st.line_chart(pd.DataFrame(data))

    except requests.exceptions.RequestException as e:
        st.error(f"无法连接到后端: {e}")
```

---

## 🧠 速查口诀表
| 需求 | 写法 |
| ---- | ---- |
| 普通文字 | `st.write()` |
| 页面大标题 | `st.title()` |
| 可交互表格 | `st.dataframe()` |
| 折线图表 | `st.line_chart()` |
| 下拉单选 | `st.selectbox()` |
| 组件放入侧边栏 | `st.sidebar.xxx()` |
| 接口缓存、防止重复请求 | `@st.cache_data` |

