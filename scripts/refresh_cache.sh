#!/bin/bash
# refresh_cache.sh — 缓存刷新脚本 [待完善]
#
# 用途：手动刷新 Ergast / FastF1 缓存数据
# 用法：bash scripts/refresh_cache.sh [ergast|fastf1|all]
#
# 当前仅清理结果缓存，Ergast 永久缓存需手动指定 --force

CACHE_DIR="./cache"

case "$1" in
  ergast)
    echo "清空 Ergast 缓存..."
    rm -rf "$CACHE_DIR/ergast_cache/"*.json
    echo "Ergast 缓存已清空，下次请求将重新拉取。"
    ;;
  fastf1)
    echo "清空 FastF1 结果缓存..."
    rm -rf "$CACHE_DIR/fastf1_result_cache/"*.json
    echo "FastF1 结果缓存已清空（原始 .ff1pkl 保留）。"
    ;;
  all)
    echo "清空所有缓存..."
    rm -rf "$CACHE_DIR/ergast_cache/"*.json
    rm -rf "$CACHE_DIR/fastf1_result_cache/"*.json
    echo "所有结果缓存已清空。"
    ;;
  *)
    echo "用法: bash scripts/refresh_cache.sh [ergast|fastf1|all]"
    exit 1
    ;;
esac
