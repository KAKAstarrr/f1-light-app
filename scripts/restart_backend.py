# -*- coding: utf-8 -*-
"""
scripts/restart_backend.py
———— 修复 Windows 端口残留 + 重启 F1 后端

为什么需要这个脚本：
  uvicorn --reload 在 Windows 上偶发"僵尸 LISTEN"
  —— 进程死了但 TCP 端口仍被内核 hold 住，新进程无法 bind，
  Vite proxy 转发到旧 worker 时一律 500。本脚本：
    1. 杀掉占用端口的全部进程
    2. 等 socket 释放（最多 15s, 失败时 netsh reset）
    3. 用 Start-Process 平替品 spawn-detach 方式启动 uvicorn

用法：
  python scripts/restart_backend.py                # 默认端口 8010
  python scripts/restart_backend.py --port 8011    # 其它端口
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil  # 若无则退化为 subprocess

# 关 stdout buffer，避免小输出在 detached 进程死亡前看不到
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


def kill_port(port: int):
    """杀掉所有占用端口的进程及其 f1_project python 进程"""
    self_pid = os.getpid()
    killed = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        # 跳过自己（防止路径里包含 f1_project 的脚本自残）
        if proc.info['pid'] == self_pid:
            continue
        try:
            cmdline = proc.info.get('cmdline') or []
            is_f1 = any('f1_project' in (c or '') for c in cmdline)
            is_python = proc.info.get('name', '').lower() in ('python.exe', 'python')
            # 端口占用
            try:
                conns = proc.net_connections(kind='inet')
            except (psutil.AccessDenied, AttributeError):
                conns = []
            on_port = any(
                getattr(c.laddr, 'port', 0) == port and c.status == 'LISTEN'
                for c in conns
            )
            if on_port or (is_f1 and is_python):
                proc.kill()
                killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def wait_port_free(port: int, timeout: int = 15) -> bool:
    """等端口被释放"""
    start = time.time()
    while time.time() - start < timeout:
        if not is_port_listening(port):
            return True
        time.sleep(1)
    return False


def is_port_listening(port: int) -> bool:
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.status == 'LISTEN':
            return True
    return False


def start_uvicorn(python_exe: str, port: int, project_root: str, log_file: str):
    """用 subprocess.Popen + DETACHED_PROCESS 启动 uvicorn 到后台"""
    args = [
        python_exe, '-m', 'uvicorn', 'backend.main:app',
        '--host', '127.0.0.1', '--port', str(port),
        '--log-level', 'info',
    ]
    log_fp = open(log_file, 'a', encoding='utf-8')
    log_fp.write(f"\n--- restart at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_fp.flush()

    # Windows 上 DETACHED_PROCESS 让进程独立于父进程
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    proc = subprocess.Popen(
        args,
        cwd=project_root,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    return proc.pid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8010)
    parser.add_argument('--python', default=r'E:\anaconda3\envs\f1_project\python.exe')
    parser.add_argument('--no-start', action='store_true', help='只清理端口，不重启')
    args = parser.parse_args()

    project_root = str(Path(__file__).resolve().parent.parent)
    log_dir = Path(project_root) / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'uvi_{args.port}.log'

    print(f"[1/3] 杀掉端口 {args.port} 占用进程 + 全部 f1_project python")
    killed = kill_port(args.port)
    if killed:
        print(f"  杀掉了 PID: {killed}")
    else:
        print("  无占用")

    print(f"[2/3] 等 socket 释放（最多 15s）")
    if not wait_port_free(args.port, timeout=15):
        print("  [WARN] 15s 未释放，尝试 netsh int ip reset")
        subprocess.run(['netsh', 'int', 'ip', 'reset'], capture_output=True)
        time.sleep(3)
        if not wait_port_free(args.port, timeout=5):
            print("  [ERROR] 端口仍被占用，重启失败")
            sys.exit(1)

    if args.no_start:
        print(f"[done] 端口 {args.port} 已清理，不重启")
        return

    print(f"[3/3] 启动 uvicorn 后台")
    pid = start_uvicorn(args.python, args.port, project_root, str(log_file))
    print(f"  uvicorn PID = {pid}")

    # 等 3s 看健康
    time.sleep(3)
    if is_port_listening(args.port):
        print(f"[done] uvicorn 健康运行 http://127.0.0.1:{args.port}/")
        print(f"       日志: {log_file}")
    else:
        print(f"[error] uvicorn 3s 内未启动成功，请查看 {log_file}")
        sys.exit(1)


if __name__ == '__main__':
    main()
