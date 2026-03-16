"""支持 python -m swallowloop 运行"""

import sys

from .main import main, helloworld

if len(sys.argv) > 1 and sys.argv[1] == "--hello":
    helloworld()
else:
    main()