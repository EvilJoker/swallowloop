# SwallowLoop 代码规范

## 一、核心原则

### 1.1 代码即规范
接口签名通过代码本身定义，不在文档重复。规范只包含代码无法表达的约束、依赖方向、禁止事项。

### 1.2 质量优先
- **测试先行**：每次功能修改必须有对应测试
- **持续集成**：提交前必须运行所有测试
- **代码审查**：所有改动需要审查才能合并

---

## 二、架构规范

### 2.1 依赖方向规则

```
Interfaces ──────► Application ──────► Domain
                      ▲
                      │
                Infrastructure
```

| 依赖路径 | 是否允许 |
|----------|---------|
| Domain → Application | ❌ 禁止 |
| Domain → Infrastructure | ❌ 禁止 |
| Application → Domain | ✅ 允许 |
| Application → Infrastructure | ⚠️ 只通过接口 |
| Infrastructure → Domain接口 | ✅ 允许 |

### 2.2 模块职责

| 模块层级 | 职责 | 约束 |
|---------|------|------|
| **Domain** | 领域模型、状态机、值对象 | 不依赖任何外层 |
| **Application** | 服务编排、流程控制 | 依赖 Domain |
| **Infrastructure** | Agent、持久化、配置 | 依赖 Domain 接口 |
| **Interfaces** | Web API、WebSocket | 依赖 Application |

### 2.3 接口约束

1. **抽象接口必须用 ABC + @abstractmethod**
2. **调用方只依赖抽象接口**，不依赖具体实现
3. **禁止跨层反向依赖**

---

## 三、Python 代码规范

### 3.1 导入顺序

```python
# 1. 标准库
import os
import logging
from typing import Optional

# 2. 第三方库
import httpx
import yaml

# 3. 本项目模块（按层级从内到外）
from ...domain.model import Issue
from ...application.service import IssueService
```

### 3.2 类和函数命名

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 类名 | PascalCase | `IssueService`, `DeerFlowAgent` |
| 函数/方法 | snake_case | `get_issue`, `fetch_status` |
| 常量 | UPPER_SNAKE_CASE | `MAX_WORKERS`, `DEFAULT_TIMEOUT` |
| 私有属性 | `_camelCase` | `_repo`, `_agent` |
| 类型变量 | PascalCase | `T`, `IssueT` |

### 3.3 类型注解

- **函数参数和返回值必须注解类型**
- **避免使用 `Any`**，除非绝对必要
- **优先使用具体类型**：`list[str]` 而非 `List`

```python
# ✅ 正确
def get_issue(issue_id: str) -> Issue | None:
    pass

# ❌ 错误
def get_issue(issue_id):
    pass
```

### 3.4 异步规范

**禁止在同步函数内使用 `asyncio.run()`**

```python
# ❌ 禁止
def sync_func():
    asyncio.run(async_func())

# ✅ 正确
async def async_caller():
    await async_func()
```

### 3.5 异常处理

```python
# ✅ 正确：捕获具体异常，记录上下文
try:
    result = await client.get(url)
except httpx.TimeoutException:
    logger.warning(f"请求超时: {url}")
    return None
except httpx.HTTPError as e:
    logger.error(f"HTTP 错误: {e}")
    raise

# ❌ 错误：捕获所有异常并静默处理
try:
    result = await client.get(url)
except Exception:
    pass
```

### 3.6 日志规范

```python
# ✅ 正确：使用结构化日志
logger.info(f"Issue 创建成功: {issue_id}")
logger.warning(f"DeerFlow 连接失败: {e}")

# 敏感信息脱敏
from ...infrastructure.logging_utils import sanitize_log_message
logger.debug(f"Task message: {sanitize_log_message(task_message)}")
```

### 3.7 常量定义

**硬编码值必须定义为具名常量**：

```python
# ✅ 正确
from ...infrastructure.constants import HttpTimeout, DEFAULT_DEERFLOW_BASE_URL

async with httpx.AsyncClient(timeout=HttpTimeout.HEALTH_CHECK) as client:
    ...

# ❌ 错误
async with httpx.AsyncClient(timeout=5.0) as client:
    ...
```

---

## 四、Git 规范

### 4.1 提交信息格式

```
<类型>(<模块>): <简短描述>

[可选的详细描述]
```

**类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构
- `test`: 测试相关
- `docs`: 文档相关
- `chore`: 构建/工具相关

**示例**：
```
feat(kanban): 添加 Pipeline 详情 Tab

- 新增 PipelineDetail 组件
- 在 IssueDetail 中集成 Tab
```

### 4.2 分支命名

```
<类型>/<描述>
feat/kanban-pipeline-detail
fix/issue-status-update
refactor/executor-service
```

### 4.3 提交前检查清单

- [ ] `pytest tests/ -v` 全部通过
- [ ] `python .claude/skills/architecture-design/scripts/check_contracts.py` 检查通过
- [ ] 无调试代码残留（console.log, print 等）
- [ ] 提交信息清晰描述改动内容

---

## 五、测试规范

### 5.1 测试文件组织

```
tests/
├── module/                    # 按模块名组织
│   ├── config/
│   │   └── test_config.py
│   ├── agent/
│   │   ├── test_deerflow_agent.py
│   │   └── test_mock_agent.py
│   └── ...
├── integration/              # 模块协作测试
└── e2e/                    # 端到端测试
```

### 5.2 测试命名

```python
class TestIssueService:
    """IssueService 功能测试"""

    def test_create_issue_success(self):
        """成功创建 Issue"""

    def test_create_issue_with_empty_title_raises(self):
        """空标题抛出异常"""
```

### 5.3 Mock 规范

```python
# ✅ 正确：mock 外部依赖，不 mock 正在测试的模块
with patch("httpx.AsyncClient") as mock_client:
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    result = await instance.fetch_usage()

# ❌ 错误：mock 路径不正确
with patch("httpx.AsyncClient", return_value=mock_context):
```

### 5.4 测试覆盖率要求

- **新功能**：必须包含单元测试
- **Bug 修复**：必须包含复现 bug 的测试
- **关键路径**：核心业务逻辑必须 100% 覆盖

---

## 六、配置规范

### 6.1 环境变量命名

| 配置项 | 环境变量 | 类型 | 说明 |
|--------|---------|------|------|
| GitHub Token | `GITHUB_TOKEN` | str | 必需 |
| 目标仓库 | `REPOS` | str | owner/repo 格式 |
| Agent 类型 | `AGENT_TYPE` | str | mock/deerflow |
| LLM 提供商 | `LLM_PROVIDER` | str | minimax/openai |
| LLM API Key | `LLM_API_KEY` | str | API 密钥 |
| DeerFlow 地址 | `DEERFLOW_BASE_URL` | str | 默认 http://localhost:2026 |

### 6.2 配置文件

| 文件 | 说明 |
|------|------|
| `.env` | 用户配置（不提交到 git） |
| `.env.template` | 配置模板 |
| `config.yaml` | 业务配置 |

---

## 七、禁止事项清单

| # | 禁止行为 | 正确做法 |
|---|---------|---------|
| 1 | 跨层反向依赖 | 依赖只能向内 |
| 2 | 直接注入具体实现 | 注入抽象接口 |
| 3 | 同步函数内使用 `asyncio.run()` | 保持异步风格 |
| 4 | 硬编码敏感信息 | 使用配置文件 |
| 5 | 硬编码魔法数字 | 定义具名常量 |
| 6 | `except Exception: pass` | 捕获具体异常 |
| 7 | 直接访问私有属性 | 使用公共接口 |
| 8 | 全局可变状态 | 通过参数传递 |
| 9 | 不带类型注解的函数 | 添加类型注解 |
| 10 | 直接提交 `.env` | 使用 `.env.template` |

---

## 八、代码审查检查清单

### 8.1 修改前

- [ ] 改动在哪个模块？
- [ ] 这个模块的接口是谁？调用方是谁？
- [ ] 会不会破坏依赖方向？
- [ ] 需不需要同步修改调用方？

### 8.2 修改后

- [ ] 新接口有测试覆盖吗？
- [ ] 测试通过了吗？
- [ ] 架构契约检查通过了吗？
- [ ] 代码风格一致吗？

---

## 九、常见问题处理

### Q: 什么时候用 `Optional[X]` vs `X | None`?
A: Python 3.10+ 推荐使用 `X | None`，旧版本用 `Optional[X]`。

### Q: 什么时候用 `ABC` vs Protocol?
A: 需要强制实现时用 `ABC`，仅声明接口契约时用 `Protocol`。

### Q: 循环依赖怎么办？
A: 使用 `TYPE_CHECKING` 导入打破循环：
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...domain.model import Issue
```
