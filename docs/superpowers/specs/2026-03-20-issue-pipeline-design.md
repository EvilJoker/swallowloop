# Issue 流水线系统设计

## 概述

SwallowLoop 的核心是一个 7 阶段流水线系统，每个 Issue 经过以下阶段：

```
头脑风暴 → 方案成型 → 详细设计 → 任务拆分 → 执行 → 更新文档 → 提交
```

用户在每个阶段审批 AI 的产出，通过后自动进入下一阶段。

## 领域模型

### TodoItem 数据结构

```python
@dataclass
class TodoItem:
    id: str
    content: str
    status: TodoStatus  # "pending" | "in_progress" | "completed" | "failed"

class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Issue 聚合根

```python
class Stage(Enum):
    BRAINSTORM = "brainstorm"
    PLAN_FORMED = "planFormed"
    DETAILED_DESIGN = "detailedDesign"
    TASK_SPLIT = "taskSplit"
    EXECUTION = "execution"
    UPDATE_DOCS = "updateDocs"
    SUBMIT = "submit"

class StageStatus(Enum):
    PENDING = "pending"      # 待审批
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"   # 已打回
    RUNNING = "running"     # 执行中

class IssueStatus(Enum):
    ACTIVE = "active"       # 活跃
    ARCHIVED = "archived"   # 已归档
    DISCARDED = "discarded" # 已废弃

@dataclass
class Comment:
    id: str
    stage: Stage
    action: str  # "approve" | "reject"
    content: str
    created_at: datetime

@dataclass
class StageState:
    stage: Stage
    status: StageStatus
    document: str = ""      # Markdown 文档
    comments: list[Comment] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    todo_list: list[TodoItem] | None = None
    progress: int | None = None

@dataclass
class Issue:
    id: str
    title: str
    description: str
    status: IssueStatus
    current_stage: Stage
    created_at: datetime
    archived_at: datetime | None = None
    discarded_at: datetime | None = None
    stages: dict[Stage, StageState]
```

### Issue 业务方法

```python
class Issue:
    def approve_stage(self, stage: Stage, comment: str = ""):
        """审批通过阶段"""

    def reject_stage(self, stage: Stage, reason: str):
        """打回阶段，附带原因"""

    def trigger_ai(self, stage: Stage):
        """手动触发 AI 执行"""

    def advance_to_next_stage(self):
        """进入下一阶段"""
```

### IssueService 接口

```python
class IssueService:
    """Issue 应用服务"""

    def list_issues(self) -> list[Issue]:
        """获取所有 Issue"""

    def get_issue(self, issue_id: str) -> Issue | None:
        """获取单个 Issue"""

    def create_issue(self, title: str, description: str) -> Issue:
        """创建新 Issue"""

    def update_issue(self, issue_id: str, **kwargs) -> Issue | None:
        """更新 Issue"""

    def delete_issue(self, issue_id: str) -> bool:
        """删除 Issue"""

    def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        """审批通过阶段，自动触发下一阶段 AI"""

    def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        """打回阶段"""

    def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        """手动触发 AI 执行当前阶段"""
```

### ExecutorService 接口

```python
class ExecutorService:
    """AI 执行服务，负责管理 IFlow Agent"""

    def __init__(self, iflow_agent: IFlowAgent):
        self._agent = iflow_agent

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """
        执行指定阶段

        流程：
        1. 读取指令文件
        2. 生成 context.md
        3. 调用 IFlow Agent
        4. 收集产出
        5. 更新 document 字段
        """
```

### 错误处理

| 场景 | 处理方式 |
|------|----------|
| AI 执行失败 | 阶段 status 设为 "error"，用户可手动重试 |
| 文件写入冲突 | 使用文件锁（fcntl.flock） |
| WebSocket 断开 | 前端自动重连，服务器保留最近 100 条日志 |
| JSON 解析失败 | 备份损坏文件，创建一个新的空结构 |

### 并发控制

- 使用 `fcntl.flock` 对 `issues.json` 加锁
- 读操作：共享锁
- 写操作：独占锁

## 持久化

### 文件结构

```
~/.swallowloop/{project}/
└── issues.json          # Issue 数据

~/.swallowloop/instructions/   # 系统预置指令
├── brainstorm.md
├── planFormed.md
├── detailedDesign.md
├── taskSplit.md
├── execution.md
├── updateDocs.md
└── submit.md
```

### issues.json 结构

```json
{
  "issues": [
    {
      "id": "issue-1",
      "title": "实现用户登录功能",
      "description": "需要实现完整的用户登录注册流程",
      "status": "active",
      "currentStage": "brainstorm",
      "createdAt": "2026-03-18T00:00:00",
      "archivedAt": null,
      "discardedAt": null,
      "stages": {
        "brainstorm": {
          "stage": "brainstorm",
          "status": "running",
          "document": "# 用户登录功能方案\n\n...",
          "comments": [],
          "startedAt": "2026-03-18T10:00:00",
          "completedAt": null,
          "todoList": null,
          "progress": null
        }
      }
    }
  ]
}
```

## 工作空间

### 目录结构

```
~/.swallowloop/{project}/{issue_id}/
└── stages/
    ├── brainstorm/
    │   ├── context.md   # AI 执行上下文
    │   └── output.md   # AI 产出
    ├── planFormed/
    │   ├── context.md
    │   └── output.md
    └── ... (7个阶段)
```

### 文件用途

| 文件 | 用途 |
|------|------|
| `context.md` | AI 执行时读取的上下文（包含指令 + 内容） |
| `output.md` | AI 产出结果 |

### 文件生成时机

1. **进入新阶段时**：
   - 将上一阶段的 `output.md` 复制为当前阶段的输入参考
   - 从 `document` 字段恢复上下文到 `context.md`

2. **阶段完成时**：
   - AI 产出从 `output.md` 读取
   - 更新 `document` 字段

## 指令文件

系统预置指令，位于 `~/.swallowloop/instructions/`

### brainstorm.md 示例

```markdown
# 头脑风暴阶段指令

## 目标
根据 Issue 描述，生成多个可行的解决方案。

## 输入
- Issue 描述：{issue_description}
- 相关上下文：见 context.md

## 输出要求
1. 列出 2-5 个可行方案
2. 每个方案包含：方案名称、核心思路、优缺点
3. 使用 Markdown 格式

## 执行方式
1. 分析 Issue 描述
2. 考虑多种技术路径
3. 输出结构化方案
```

### execution.md 示例

```markdown
# 执行阶段指令

## 目标
根据任务拆分阶段的 TODO 列表，执行代码任务。

## 输入
- TODO 列表：见 context.md
- 上一阶段产出：见 ../taskSplit/output.md

## 执行方式
循环执行每个 TODO：
1. 读取当前 TODO 内容
2. 执行代码修改
3. 完成后标记状态
4. 进入下一个 TODO

## 输出要求
1. 更新 TODO 状态
2. 记录执行日志
3. 产出代码变更
```

## 执行流程

### 阶段流转

```
用户审批通过
    ↓
IssueService.approve_stage()
    ↓
更新阶段状态: status = "approved"
    ↓
advance_to_next_stage()
    ↓
创建 context.md
    ↓
自动触发 IFlow Agent
```

### AI 执行流程

```
1. 读取 ~/.swallowloop/instructions/{stage}.md
2. 读取 ~/.swallowloop/{project}/{issue_id}/stages/{stage}/context.md
3. 读取上一阶段的 output.md（如有）
4. 执行任务
5. 产出写入 output.md
6. 更新 document 字段
```

### 执行时序图

```
用户审批通过
    │
    ▼
IssueService.approve_stage()
    │
    ├─► 更新 Issue 状态 (approved)
    │
    ├─► advance_to_next_stage()
    │
    ├─► FileManager.prepare_stage_context()
    │       │
    │       └─► 复制上一阶段 output.md
    │       └─► 生成 context.md
    │
    ▼
ExecutorService.execute_stage()
    │
    ├─► IFlowAgent.execute(
    │       instruction=instruction.md,
    │       context=context.md
    │   )
    │
    ├─► 实时日志通过 WebSocket 推送
    │
    └─► 完成后更新 document 字段
```

### 执行阶段特殊处理

- **循环执行**：每个 TODO 单独执行一次
- **进度追踪**：通过 `todo_list` 和 `progress` 字段跟踪
- **手动触发**：`trigger_ai()` 可在任何阶段手动触发

### 打回流程

```
用户点击"打回"并填写原因
    ↓
IssueService.reject_stage(reason)
    ↓
更新状态: status = "rejected"
    ↓
添加 Comment 到当前阶段
    ↓
AI 执行时读取最新 reject 原因的 comment
```

## 接口设计

### REST API

```
GET    /api/issues                    # 列表
GET    /api/issues/{id}               # 详情
POST   /api/issues                    # 创建
PATCH  /api/issues/{id}               # 更新（归档/废弃）
DELETE /api/issues/{id}               # 删除

POST   /api/issues/{id}/trigger       # 手动触发 AI
POST   /api/issues/{id}/stages/{stage}/approve   # 审批通过
POST   /api/issues/{id}/stages/{stage}/reject    # 审批打回
```

### WebSocket

```
WS /ws/execution/{issue_id}          # 执行日志流
```

## 目录结构

```
src/swallowloop/
├── domain/
│   ├── model/
│   │   ├── issue.py           # Issue 聚合根
│   │   ├── stage.py           # Stage 值对象
│   │   └── comment.py         # Comment 值对象
│   └── repository/
│       └── issue_repository.py # Issue 仓库接口
│
├── application/
│   ├── service/
│   │   ├── issue_service.py   # Issue 应用服务
│   │   └── executor_service.py # AI 执行服务（调用 IFlow）
│   └── dto/
│       └── issue_dto.py       # 数据传输对象
│
├── infrastructure/
│   ├── persistence/
│   │   ├── json_issue_repository.py  # JSON 持久化（含文件锁）
│   │   └── file_manager.py   # 工作空间文件管理
│   ├── agent/
│   │   └── iflow/
│   │       └── iflow_agent.py # IFlow Agent 封装
│   └── config/
│       └── settings.py        # 配置管理
│
└── interfaces/
    └── web/
        ├── dashboard.py       # Web Dashboard（扩展）
        └── api/
            ├── issues.py      # Issue API 路由
            └── websockets.py  # WebSocket 处理
```

### 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                    IssueService                         │
│  ( orchestrates the entire flow )                       │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌─────────────────┐
│ IFlowAgent    │   │ ExecutorService │
│ (low-level    │   │ (stage context  │
│  agent exec)   │   │  management)    │
└───────────────┘   └─────────────────┘
```

- **IssueService**：编排整个流程，处理 API 请求，管理 Issue 状态
- **ExecutorService**：管理阶段上下文，调用 IFlowAgent，处理执行逻辑
- **IFlowAgent**：纯粹的 Agent 执行封装，不了解 Issue 概念

## 关键设计决策

1. **混合存储**：
   - `document` 字段存储 JSON，方便 API 查询
   - 文件系统存储工作空间，供 Agent 读写

2. **指令预置**：
   - 每个阶段有独立的指令文件
   - Agent 读取对应阶段的指令执行

3. **循环执行**：
   - 执行阶段按 TODO 循环
   - 用户可查看进度、被打断

4. **评论驱动**：
   - 打回原因存储在 `comments` 字段
   - AI 通过读取评论获取修改意见
