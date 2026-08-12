import fastf1
import os

CACHE_DIR = "./cache/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.set_log_level("Warning")

try:
    # 测试你接口请求的 2026 第1站
    session = fastf1.get_session(2026, 1, "R")
    session.load(laps=True, telemetry=False)
    print("圈速行数：", len(session.laps))
except Exception as e:
    print("加载异常：", e)
