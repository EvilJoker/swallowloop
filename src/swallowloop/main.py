"""SwallowLoop 入口"""

import os
import sys

import psutil

from .config import Config
from .orchestrator import Orchestrator


def kill_existing_processes() -> None:
    """杀死已存在的 swallowloop 进程"""
    current_pid = os.getpid()
    killed = False

    for proc in psutil.process_iter(["pid", "exe", "cmdline"]):
        try:
            exe = proc.info.get("exe") or ""
            cmdline = proc.info.get("cmdline") or []
            
            # 跳过 VSCode 扩展进程
            cmdline_str = " ".join(cmdline).lower()
            if "vscode" in cmdline_str or "lsp_server" in cmdline_str:
                continue

            # 检查是否是真正的 swallowloop 入口点
            is_entry = exe.endswith("/swallowloop") or "bin/swallowloop" in exe
            
            if is_entry and proc.info["pid"] != current_pid:
                print(f"[KILL] 终止旧进程: PID={proc.info['pid']}")
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        import time

        time.sleep(1)  # 等待进程完全退出


def main():
    """主入口"""
    kill_existing_processes()
    config = Config.from_env()
    orchestrator = Orchestrator(config)
    orchestrator.run()


if __name__ == "__main__":
    main()