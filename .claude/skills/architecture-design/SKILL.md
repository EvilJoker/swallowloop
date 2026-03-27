---
name: architecture-design
description: 模块化架构设计技能，包含接口规范、依赖方向、契约检查和自检机制。适用于设计新模块、审查代码改动，重构时保证架构一致性。
---

# 架构设计技能

## 核心原则

**代码即规范**：接口签名通过代码本身定义，不在文档重复。
**规范只包含**：代码无法表达的约束、依赖方向、禁止事项。

---

## 1. 模块职责定义

每个模块必须职责单一，边界清晰：

| 模块层级 | 职责 | 约束 |
|---------|------|------|
| Domain | 领域模型、状态机、值对象 | 不依赖任何外层 |
| Application | 服务编排、流程控制 | 依赖 Domain |
| Infrastructure | Agent、持久化、配置 | 依赖 Domain 接口 |
| Interfaces | Web API、WebSocket | 依赖 Application |

---

## 2. 依赖方向规则

```
Interfaces ──────► Application ──────► Domain
                      ▲
                      │
                Infrastructure
```

**规则**：依赖只能向内，不能向外。

| 依赖路径 | 是否允许 |
|----------|---------|
| Domain → Application | ❌ 禁止 |
| Domain → Infrastructure | ❌ 禁止 |
| Application → Domain | ✅ 允许 |
| Application → Infrastructure | ⚠️ 只通过接口 |
| Infrastructure → Domain接口 | ✅ 允许 |

---

## 3. 接口约束（通过代码实现）

### 3.1 抽象接口必须用 ABC + @abstractmethod

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    async def prepare(self, issue_id: str, context: dict) -> WorkspaceInfo:
        """所有 Agent 必须实现此方法"""
        pass
```

### 3.2 调用方只依赖抽象接口

```python
# ✅ 正确：声明类型为抽象接口
class ExecutorService:
    def __init__(self, agent: BaseAgent):
        self._agent = agent

# ❌ 错误：直接依赖具体实现
class ExecutorService:
    def __init__(self, agent: MockAgent):
        self._agent = agent
```

---

## 4. 禁止事项

1. **跨层反向依赖**
   ```python
   # ❌ 禁止：Infrastructure 依赖 Application
   from application.service import IssueService
   ```

2. **具体实现注入**
   ```python
   # ❌ 禁止
   service = ExecutorService(agent=MockAgent())

   # ✅ 正确：注入抽象接口
   service = ExecutorService(agent=BaseAgent)  # 运行时传入具体实现
   ```

3. **在同步函数内使用 asyncio.run()**
   ```python
   # ❌ 禁止
   def sync_func():
       asyncio.run(async_func())

   # ✅ 正确：保持异步风格，或使用正确的事件循环管理
   async def async_caller():
       await async_func()
   ```

4. **模块间共享可变状态**
   ```python
   # ❌ 禁止：全局可变状态
   _global_state = {}

   # ✅ 正确：通过参数传递
   def process(issue, stage, state):
       ...
   ```

---

## 5. 修改检查清单

**修改代码前必须问自己**：

- [ ] 改动的代码在哪个模块？
- [ ] 这个模块的接口是谁？调用方是谁？
- [ ] 会不会破坏依赖方向？
- [ ] 需不需要同步修改调用方？
- [ ] 测试能发现这个问题吗？

---

## 6. 自检机制

### 6.1 运行契约检查

项目根目录下运行：

```bash
python .claude/skills/architecture-design/scripts/check_contracts.py
```

检查内容：
- 依赖方向是否正确
- Agent 接口实现是否完整
- 是否在同步函数中使用了 asyncio.run()
- 是否直接注入了具体实现

### 6.2 运行测试

```bash
./run.sh test
# 或
pytest tests/ -v
```

---

## 7. 接口变更流程

当需要修改接口时：

1. **分析影响范围**：这个接口被几个模块调用？
2. **同步修改**：所有调用方一起改
3. **更新测试**：确保测试覆盖新接口
4. **运行验证**：`python .claude/skills/architecture-design/scripts/check_contracts.py` + `./run.sh test`

---

## 8. 适用场景

使用此技能当：

- 设计新模块或新接口
- 审查代码改动
- 重构代码
- 添加新的 Agent 实现（如 MockAgent → DeerFlowAgent）
- 修改跨模块调用

**不使用**当：
- 修改单个模块内部实现，不影响接口
- 简单的 bug fix
- 纯 UI 修改
