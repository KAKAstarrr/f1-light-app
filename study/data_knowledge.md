# NumPy + Pandas + Matplotlib 核心知识点手册（适配F1项目）
> 适用场景：F1圈速/遥测数据清洗、统计绘图、AI特征工程；剔除网课冗余理论，全部可直接复制运行

## 一、NumPy（底层数组）
### 1. 核心对象 ndarray
```python
import numpy as np
# 项目最常用：从Pandas列转为numpy数组
# lap_sec = laps["LapTime"].dt.total_seconds().to_numpy()

# 手动创建数组
arr = np.array([98.1,97.5,98.6])

# 切片索引（筛选圈次）
arr[:10]         # 前10个元素
arr[2:5]         # 第2~4个元素
arr[arr < 98]    # 条件筛选，选出小于98秒的圈速

# 常用统计函数
np.mean(arr)        # 平均值
np.min(arr)         # 最小值
np.max(arr)         # 最大值
np.nanmean(arr)     # 忽略空值计算平均

# 广播运算（无需循环批量计算）
arr - np.min(arr)   # 每一圈减去最快圈，计算和最快圈差距
```
✅ **项目用途**：批量圈速差值计算、构造二维数据集供给XGBoost模型
❌ **不用学习**：高维数组、矩阵求逆、傅里叶变换

---

## 二、Pandas（处理fastf1核心库）
fastf1加载得到的 `laps` 数据类型为 **DataFrame**
### 1. 基础查看
```python
laps.head()       # 查看前5行数据
laps.columns      # 查看所有列名称
laps.shape        # 返回 (行数,列数)
```

### 2. 数据筛选（最高频操作）
```python
# 单条件筛选：筛选VER车手全部圈数据
ver_laps = laps[laps["Driver"] == "VER"]

# 多条件筛选【项目固定清洗模板】有效计时圈
valid_laps = laps[(laps["LapTime"].notna()) & (laps["PitInTime"].isna())]

# 提取指定多列
simple = laps[["Driver","LapNumber","LapTime"]]
```

### 3. 时间类型转换（fastf1专属）
```python
# TimeDelta时间格式 → 总秒数
laps["LapTime"].dt.total_seconds()
```
⚠️ **重要禁忌**：`groupby`分组后的对象**不能直接调用 `.dt`**
> 正确流程：先把时间转为秒，再执行分组！

### 4. groupby 分组聚合（车手统计、轮胎分析核心）
```python
# 标准写法
valid_laps["lap_sec"] = valid_laps["LapTime"].dt.total_seconds()

# 按车手分组，统计平均圈速、最快圈
group = valid_laps.groupby("Driver")["lap_sec"]
stat = group.agg(["mean","min"])

# 按轮胎类型分组，求取平均圈速
tire_stat = valid_laps.groupby("Compound")["lap_sec"].mean()
```

### 5. 基础数据清洗
```python
laps.dropna(subset=["LapTime"]) # 删除圈速为空的无效行
```
❌ **不用学习**：透视表、多表合并、复杂分层索引

---

## 三、Matplotlib 绘图（生成前端可视化图表）
### 1. 全局前置配置（解决中文方框乱码，所有绘图代码开头必加）
```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ["SimHei"]
plt.rcParams['axes.unicode_minus'] = False
```

### 2. 通用标准绘图模板
```python
# 1. 创建画布
plt.figure(figsize=(10,4))

# 2. 绘制图形
plt.plot(x轴数据,y轴数据,label="名称")       # 折线图
plt.bar(x,y)                                # 柱状图
plt.pie(values,labels=标签,autopct="%1.1f%%") # 饼图

# 3. 图表美化
plt.title("标题")
plt.xlabel("横轴名称")
plt.ylabel("纵轴名称")
plt.legend() # 显示图例

# 4. 输出
plt.savefig("图片路径.png") # 保存图片文件
plt.show()                  # Notebook预览图片
```
⚠️ **避坑要点**
1. `plt.rcParams` 写在绘图代码**最前面**
2. 优先执行 `plt.figure()` 创建画布，再绘图
3. 调试完成的绘图代码，可以封装成函数给FastAPI后端调用

❌ **不用学习**：3D绘图、动态交互图

---

## 四、F1项目通用启动模板（直接复制运行）
```python
import fastf1
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# matplotlib中文配置
plt.rcParams['font.sans-serif'] = ["SimHei"]
plt.rcParams['axes.unicode_minus'] = False

# fastf1缓存配置
fastf1.Cache.enable_cache("cache")
# 加载比赛数据
session = fastf1.get_session(2025, "Bahrain", "R")
session.load()
laps = session.laps

# 数据清洗：有效计时圈
valid_laps = laps[(laps["LapTime"].notna()) & (laps["PitInTime"].isna())]
valid_laps["lap_sec"] = valid_laps["LapTime"].dt.total_seconds()
```

---

## 五、高频踩坑汇总（你已经遇到的问题）
1. ❌ `groupby` 对象无法调用 `.dt`
✅ 解决方案：先将时间转换成秒，再分组
2. ❌ 清洗数据后仍然出现 `nan`
✅ 解决方案：后续代码使用清洗后的 `valid_laps`，不要继续使用原始 `laps`
3. ❌ Matplotlib中文显示方框
✅ 解决方案：增加字体两行配置，放在绘图代码最上方
4. ❌ `NotADirectoryError`
✅ 解决方案：手动新建cache文件夹，或者使用绝对路径
5. ❌ `ModuleNotFoundError`
✅ 解决方案：PyCharm解释器切换至 `fl_project` 环境

---
