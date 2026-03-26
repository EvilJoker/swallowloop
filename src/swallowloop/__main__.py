"""支持 python -m swallowloop 运行"""

import argparse

from .main import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SwallowLoop")
    parser.add_argument("--port", type=int, default=9500, help="Web 服务器端口")
    args = parser.parse_args()

    main(port=args.port)
