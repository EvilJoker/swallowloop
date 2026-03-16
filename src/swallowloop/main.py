"""SwallowLoop 入口"""

import sys

from .interfaces.cli.orchestrator import main


def helloworld() -> None:
    """打印 Hello World"""
    print("Hello, World! Welcome to SwallowLoop!")


if __name__ == "__main__":
    # 支持 python -m swallowloop --hello 参数
    if len(sys.argv) > 1 and sys.argv[1] == "--hello":
        helloworld()
    else:
        main()