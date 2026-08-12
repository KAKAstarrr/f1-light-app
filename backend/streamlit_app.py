import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']   # 黑体支持中文
plt.rcParams['axes.unicode_minus'] = False     # 解决负号显示异常

st.set_page_config(page_title="F1 数据看板（MVP）",layout="wide")
st.title("🏎️ F1 数据可视化看板")

BASE_URL="http://localhost:8000"
st.write("welcome to Formula One")

# --- 缓存机制 (优化加载速度) ---
@st.cache_data(ttl=600)
def fetch_api_data(endpoint: str):
    """封装 API 请求"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ 后端连接失败: {e}")
        return None

# ================= S.2 知识点：DataFrame / Table 赛程看板 =================
st.header("S.2 赛程列表看板")
schedule_data= fetch_api_data("/api/current-season")
if schedule_data and 'Races' in schedule_data:
    races=schedule_data['Races']
    df=pd.DataFrame([
        {
            'Round':r['round'],
            '赛道':r['raceName'],
            '国家':r['Circuit']['Location']['country'],
            '日期':r['date']
        }
        for r in races
    ])
    st.subheader("当前赛季完整赛历")
    st.dataframe(df,use_container_width=True)
    st.subheader("首站详情")
    st.table(df.head(5))
else:
    st.warning("等待赛程数据。。。。")

st.divider()
# ================= S.3 知识点：Metric / 分栏布局 =================
st.header("S.3 比赛结果与积分榜")

col1,col2,col3=st.columns(3)
with col1:
    # 模拟比赛结果数据
    st.metric(label="🏆 冠军", value="VER", delta="+15.2s")
with col2:
    st.metric(label="🥈 亚军", value="NOR", delta="Finish")
with col3:
    st.metric(label="🥉 季军", value="LEC")

st.subheader("车队积分榜模拟")
teams = ["Red Bull", "Ferrari", "Mercedes", "McLaren"]
points = [520, 480, 420, 380]

fig, ax = plt.subplots()
ax.barh(teams,points,color=['#1E41FF', '#DC143C', '#00D2BE', '#FF8700'])
ax.invert_yaxis()
st.pyplot(fig)

st.divider()
# ================= S.4 知识点：Bar Chart + Matplotlib 嵌入 =================
st.header("S.4 轮胎策略可视化")
# 模拟轮胎策略数据
tyre_data = pd.DataFrame({
    'Stint': ['1', '2', '3', '4'],
    'Compound': ['Soft', 'Medium', 'Hard', 'Soft'],
    'Laps': [12, 18, 20, 10]
})
fig,ax = plt.subplots(figsize=(10,4))
colors = {'Soft': '#FF3333', 'Medium': '#FFF200', 'Hard': '#0072C6'}
tyre_data.plot(kind='bar',x='Stint',y='Laps',color=[colors[i] for i in tyre_data['Compound']], ax=ax, legend=False)
ax.set_title("进站策略与圈数分布")
ax.set_xlabel("Stint (进站段)")
ax.set_ylabel("Laps")

st.pyplot(fig)
st.dataframe(tyre_data, use_container_width=True)
st.divider()
# ================= S.5 知识点：Progress / 柱状图 =================
st.header("S.5 AI 预测概率展示")

# 模拟 AI 预测任务
progress_bar = st.progress(0, text="正在初始化模型...")
for i in range(100):
    progress_bar.progress(i + 1, text=f"计算中... {i+1}%")
    time.sleep(0.01)
st.success("✅ 预测完成！")

st.subheader("比赛结果预测概率")
# 模拟预测数据
probs = pd.DataFrame({
    'Outcome': ['Verstappen Win', 'Norris Win', ' Perez Win', 'Other'],
    'Probability': [0.65, 0.20, 0.10, 0.05]
})
# 绘制预测概率柱状图
st.bar_chart(probs.set_index('Outcome'))

# 结论展示
st.info("AI 预测结论：维斯塔潘胜率最高 (65%)", icon="💡")

# @st.cache_data
# def load_driver_names():
#     res = requests.get(BASE_URL+"/api/current/drivers").json()
#     df = pd.DataFrame(res["Drivers"])
#     return df
#
# driver_df = load_driver_names()
#
# st.sidebar.header("面板")
# driver=st.sidebar.selectbox(
#     "选择车手",
#     driver_df["driverId"],
# )
#
# st.dataframe(
#     driver_df,
#     column_config={
#         "code":st.column_config.TextColumn("车手代码"),
#         'permanentNumber':st.column_config.TextColumn("车号"),
#         "driverId":"名"
#     },
#     use_container_width=True
# )
# st.write(f"Selected: {driver}")
#
# if st.sidebar.button("获取数据"):
#     st.subheader("车手信息")
#     st.dataframe(driver_df)



# drivers = st.multiselect(
#     "选择对比车手:",
#     names,
#     default=["VER", "HAM"], # 默认选中
#     key="driver_multi"
# )

