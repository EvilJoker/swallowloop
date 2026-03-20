# Issue 流水线系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 7 阶段 Issue 流水线系统，支持审批后自动触发 AI 执行

**Architecture:** 采用 DDD 架构，Issue 作为聚合根，StageState 作为子实体，ExecutorService 编排 IFlow Agent 执行。使用 JSON 文件持久化 + 文件系统存储工作空间。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, transitions, fcntl (文件锁)

---

## 文件结构

```
src/swallowloop/
├── domain/
│   └── model/
│       ├── issue.py           # 新增：Issue 聚合根
│       ├── stage.py           # 新增：Stage 枚举
│       └── comment.py         # 新增：Comment 值对象
│   └── repository/
│       └── issue_repository.py # 新增：IssueRepository 接口
│
├── application/
│   ├── service/
│   │   ├── issue_service.py   # 新增：IssueService
│   │   └── executor_service.py # 新增：ExecutorService
│   └── dto/
│       └── issue_dto.py       # 新增：IssueDTO
│
├── infrastructure/
│   ├── persistence/
│   │   └── json_issue_repository.py  # 新增：JsonIssueRepository
│   ├── agent/
│   │   └── iflow/
│   │       └── iflow_agent.py # 修改：适配 Issue 执行
│   └── config/
│       └── settings.py        # 修改：添加 Issue 相关配置
│
└── interfaces/
    └── web/
        └── dashboard.py       # 修改：添加 Issue API 端点

~/.swallowloop/
├── instructions/               # 新增：系统预置指令
│   ├── brainstorm.md
│   ├── planFormed.md
│   ├── detailedDesign.md
│   ├── taskSplit.md
│   ├── execution.md
│   ├── updateDocs.md
│   └── submit.md
└── {project}/
    └── issues.json           # Issue 数据
```

---

## Task 1: 领域模型 - Stage 枚举和值对象

**Files:**
- Create: `src/swallowloop/domain/model/stage.py`
- Modify: `src/swallowloop/domain/model/__init__.py`

- [ ] **Step 1: 创建 stage.py**

```python
"""Stage 和相关枚举定义"""

from enum import Enum
from typing import Literal


class Stage(Enum):
    """Issue 流水线阶段"""
    BRAINSTORM = "brainstorm"
    PLAN_FORMED = "planFormed"
    DETAILED_DESIGN = "detailedDesign"
    TASK_SPLIT = "taskSplit"
    EXECUTION = "execution"
    UPDATE_DOCS = "updateDocs"
    SUBMIT = "submit"


class StageStatus(Enum):
    """阶段状态"""
    PENDING = "pending"      # 待审批
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已打回
    RUNNING = "running"      # 执行中
    ERROR = "error"          # 异常


class IssueStatus(Enum):
    """Issue 状态"""
    ACTIVE = "active"        # 活跃
    ARCHIVED = "archived"    # 已归档
    DISCARDED = "discarded"  # 已废弃


class TodoStatus(Enum):
    """TODO 项状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionState(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .stage import Stage, StageStatus, IssueStatus, TodoStatus, ExecutionState
from .comment import Comment
from .issue import Issue, IssueId, StageState, TodoItem
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/domain/model/stage.py src/swallowloop/domain/model/__init__.py
git commit -m "feat(domain): 添加 Stage, StageStatus, IssueStatus, TodoStatus 枚举"
```

---

## Task 2: 领域模型 - Comment 值对象

**Files:**
- Create: `src/swallowloop/domain/model/comment.py`

- [ ] **Step 1: 创建 comment.py**

```python
"""Comment 值对象"""

from dataclasses import dataclass
from datetime import datetime

from .stage import Stage


@dataclass
class Comment:
    """评论/审核意见"""
    id: str
    stage: Stage
    action: str  # "approve" | "reject"
    content: str
    created_at: datetime

    @classmethod
    def create(cls, stage: Stage, action: str, content: str) -> "Comment":
        """创建新评论"""
        import uuid
        return cls(
            id=f"comment-{uuid.uuid4().hex[:8]}",
            stage=stage,
            action=action,
            content=content,
            created_at=datetime.now(),
        )
```

- [ ] **Step 2: 提交**

```bash
git add src/swallowloop/domain/model/comment.py
git commit -m "feat(domain): 添加 Comment 值对象"
```

---

## Task 3: 领域模型 - Issue 聚合根

**Files:**
- Create: `src/swallowloop/domain/model/issue.py`
- Modify: `src/swallowloop/domain/model/__init__.py`

- [ ] **Step 1: 创建 issue.py**

```python
"""Issue 聚合根"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .stage import Stage, StageStatus, IssueStatus, TodoStatus, ExecutionState


@dataclass
class TodoItem:
    """TODO 项"""
    id: str
    content: str
    status: TodoStatus = TodoStatus.PENDING

    def mark_in_progress(self):
        self.status = TodoStatus.IN_PROGRESS

    def mark_completed(self):
        self.status = TodoStatus.COMPLETED

    def mark_failed(self):
        self.status = TodoStatus.FAILED


@dataclass
class StageState:
    """阶段状态"""
    stage: Stage
    status: StageStatus = StageStatus.PENDING
    document: str = ""
    comments: list = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    todo_list: Optional[list[TodoItem]] = None
    progress: Optional[int] = None
    execution_state: Optional[ExecutionState] = None


@dataclass
class IssueId:
    """Issue ID 值对象"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Issue:
    """Issue 聚合根"""
    id: IssueId
    title: str
    description: str
    status: IssueStatus
    current_stage: Stage
    created_at: datetime
    archived_at: Optional[datetime] = None
    discarded_at: Optional[datetime] = None
    stages: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.stages:
            self.stages = self._create_default_stages()

    def _create_default_stages(self) -> dict:
        """创建默认阶段"""
        return {s: StageState(stage=s) for s in Stage}

    def get_stage_state(self, stage: Stage) -> StageState:
        """获取阶段状态"""
        return self.stages[stage]

    def approve_stage(self, stage: Stage, comment: str = "") -> None:
        """审批通过阶段"""
        state = self.stages[stage]
        state.status = StageStatus.APPROVED
        state.completed_at = datetime.now()
        if comment:
            from .comment import Comment
            state.comments.append(Comment.create(stage, "approve", comment))

    def reject_stage(self, stage: Stage, reason: str) -> None:
        """打回阶段"""
        state = self.stages[stage]
        state.status = StageStatus.REJECTED
        if reason:
            from .comment import Comment
            state.comments.append(Comment.create(stage, "reject", reason))

    def start_stage(self, stage: Stage) -> None:
        """开始阶段执行"""
        state = self.stages[stage]
        state.status = StageStatus.RUNNING
        state.started_at = datetime.now()
        self.current_stage = stage

    def get_latest_rejection(self, stage: Stage) -> Optional[str]:
        """获取最新的打回原因"""
        state = self.stages[stage]
        for comment in reversed(state.comments):
            if comment.action == "reject":
                return comment.content
        return None

    @property
    def is_active(self) -> bool:
        """Issue 是否活跃"""
        return self.status == IssueStatus.ACTIVE
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .issue import Issue, IssueId, StageState, TodoItem
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/domain/model/issue.py src/swallowloop/domain/model/__init__.py
git commit -m "feat(domain): 添加 Issue 聚合根和 StageState, TodoItem"
```

---

## Task 4: 仓库接口 - IssueRepository

**Files:**
- Create: `src/swallowloop/domain/repository/issue_repository.py`
- Modify: `src/swallowloop/domain/repository/__init__.py`

- [ ] **Step 1: 创建 issue_repository.py**

```python
"""Issue 仓库接口"""

from abc import ABC, abstractmethod

from ..model import Issue, IssueId


class IssueRepository(ABC):
    """Issue 仓库接口"""

    @abstractmethod
    def get(self, issue_id: IssueId) -> Issue | None:
        """根据 ID 获取 Issue"""

    @abstractmethod
    def save(self, issue: Issue) -> None:
        """保存 Issue"""

    @abstractmethod
    def list_all(self) -> list[Issue]:
        """列出所有 Issue"""

    @abstractmethod
    def list_active(self) -> list[Issue]:
        """列出活跃 Issue"""

    @abstractmethod
    def delete(self, issue_id: IssueId) -> bool:
        """删除 Issue"""
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .issue_repository import IssueRepository
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/domain/repository/issue_repository.py src/swallowloop/domain/repository/__init__.py
git commit -m "feat(domain): 添加 IssueRepository 接口"
```

---

## Task 5: 持久化 - JsonIssueRepository

**Files:**
- Create: `src/swallowloop/infrastructure/persistence/json_issue_repository.py`
- Modify: `src/swallowloop/infrastructure/persistence/__init__.py`

- [ ] **Step 1: 创建 json_issue_repository.py**

```python
"""JSON Issue 仓库实现"""

import fcntl
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import IO

from ...domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus, TodoStatus
from ...domain.repository import IssueRepository

logger = logging.getLogger(__name__)


class JsonIssueRepository(IssueRepository):
    """
    JSON 文件 Issue 仓库

    数据保存到 ~/.swallowloop/{project}/issues.json
    使用文件锁保护并发写入
    """

    def __init__(self, project: str, data_dir: Path | None = None):
        self.project = project
        self.data_dir = (data_dir or Path.home() / ".swallowloop") / project
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.issues_file = self.data_dir / "issues.json"
        self._lock_file = self.data_dir / "issues.json.lock"
        self._load()

    def _load(self) -> None:
        """加载数据"""
        if not self.issues_file.exists():
            self._data = {"issues": []}
            return

        try:
            with open(self.issues_file) as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载 Issue 数据失败: {e}")
            self._data = {"issues": []}

    def _save(self) -> None:
        """保存数据（带文件锁）"""
        temp_file = self.issues_file.with_suffix('.tmp')
        lock_path = self._lock_file

        try:
            with open(lock_path, 'w') as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                try:
                    with open(temp_file, "w") as f:
                        json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)
                    temp_file.replace(self.issues_file)
                finally:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"保存 Issue 数据失败: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def get(self, issue_id: IssueId) -> Issue | None:
        """根据 ID 获取 Issue"""
        for data in self._data.get("issues", []):
            if data["id"] == str(issue_id):
                return self._deserialize(data)
        return None

    def save(self, issue: Issue) -> None:
        """保存 Issue"""
        issues = self._data.get("issues", [])
        for i, data in enumerate(issues):
            if data["id"] == str(issue.id):
                issues[i] = self._serialize(issue)
                break
        else:
            issues.append(self._serialize(issue))
        self._data["issues"] = issues
        self._save()

    def list_all(self) -> list[Issue]:
        """列出所有 Issue"""
        return [self._deserialize(d) for d in self._data.get("issues", [])]

    def list_active(self) -> list[Issue]:
        """列出活跃 Issue"""
        return [i for i in self.list_all() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        """删除 Issue"""
        issues = self._data.get("issues", [])
        original_len = len(issues)
        self._data["issues"] = [d for d in issues if d["id"] != str(issue_id)]
        if len(self._data["issues"]) < original_len:
            self._save()
            return True
        return False

    def _serialize(self, issue: Issue) -> dict:
        """序列化 Issue"""
        return {
            "id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "status": issue.status.value,
            "currentStage": issue.current_stage.value,
            "createdAt": issue.created_at.isoformat(),
            "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
            "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
            "stages": {
                stage.value: {
                    "stage": stage.value,
                    "status": state.status.value,
                    "document": state.document,
                    "comments": [
                        {
                            "id": c.id,
                            "stage": c.stage.value,
                            "action": c.action,
                            "content": c.content,
                            "createdAt": c.created_at.isoformat(),
                        }
                        for c in state.comments
                    ],
                    "startedAt": state.started_at.isoformat() if state.started_at else None,
                    "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                    "todoList": [
                        {"id": t.id, "content": t.content, "status": t.status.value}
                        for t in (state.todo_list or [])
                    ],
                    "progress": state.progress,
                    "executionState": state.execution_state.value if state.execution_state else None,
                }
                for stage, state in issue.stages.items()
            },
        }

    def _deserialize(self, data: dict) -> Issue:
        """反序列化 Issue"""
        from ...domain.model import StageState, TodoItem, Comment

        stages = {}
        for stage_str, state_data in data.get("stages", {}).items():
            stage = Stage(stage_str)
            todo_list = None
            if state_data.get("todoList"):
                todo_list = [
                    TodoItem(
                        id=t["id"],
                        content=t["content"],
                        status=TodoStatus(t["status"]),
                    )
                    for t in state_data["todoList"]
                ]

            stages[stage] = StageState(
                stage=stage,
                status=StageStatus(state_data.get("status", "pending")),
                document=state_data.get("document", ""),
                comments=[
                    Comment(
                        id=c["id"],
                        stage=Stage(c["stage"]),
                        action=c["action"],
                        content=c["content"],
                        created_at=datetime.fromisoformat(c["createdAt"]),
                    )
                    for c in state_data.get("comments", [])
                ],
                started_at=datetime.fromisoformat(state_data["startedAt"]) if state_data.get("startedAt") else None,
                completed_at=datetime.fromisoformat(state_data["completedAt"]) if state_data.get("completedAt") else None,
                todo_list=todo_list,
                progress=state_data.get("progress"),
                execution_state=ExecutionState(state_data["executionState"]) if state_data.get("executionState") else None,
            )

        issue = Issue(
            id=IssueId(data["id"]),
            title=data["title"],
            description=data.get("description", ""),
            status=IssueStatus(data.get("status", "active")),
            current_stage=Stage(data.get("currentStage", "brainstorm")),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else datetime.now(),
            archived_at=datetime.fromisoformat(data["archivedAt"]) if data.get("archivedAt") else None,
            discarded_at=datetime.fromisoformat(data["discardedAt"]) if data.get("discardedAt") else None,
            stages=stages,
        )
        return issue
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .json_issue_repository import JsonIssueRepository
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/infrastructure/persistence/json_issue_repository.py src/swallowloop/infrastructure/persistence/__init__.py
git commit -m "feat(infrastructure): 添加 JsonIssueRepository 实现"
```

---

## Task 6: 应用服务 - IssueService

**Files:**
- Create: `src/swallowloop/application/service/issue_service.py`
- Modify: `src/swallowloop/application/service/__init__.py`

- [ ] **Step 1: 创建 issue_service.py**

```python
"""Issue 应用服务"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .executor_service import ExecutorService

from ...domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from ...domain.repository import IssueRepository

logger = logging.getLogger(__name__)


class IssueService:
    """Issue 应用服务"""

    def __init__(self, repository: IssueRepository, executor: "ExecutorService"):
        self._repo = repository
        self._executor = executor

    def list_issues(self) -> list[Issue]:
        """获取所有 Issue"""
        return self._repo.list_all()

    def get_issue(self, issue_id: str) -> Issue | None:
        """获取单个 Issue"""
        return self._repo.get(IssueId(issue_id))

    def create_issue(self, title: str, description: str) -> Issue:
        """创建新 Issue"""
        issue_id = IssueId(f"issue-{uuid.uuid4().hex[:8]}")
        issue = Issue(
            id=issue_id,
            title=title,
            description=description,
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        self._repo.save(issue)
        logger.info(f"创建 Issue: {issue_id} - {title}")
        return issue

    async def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        """审批通过阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        issue.approve_stage(stage, comment)
        self._repo.save(issue)
        logger.info(f"Issue {issue_id} 阶段 {stage.value} 审批通过")

        # 自动进入下一阶段并触发 AI
        await self._advance_and_trigger(issue, stage)
        return issue

    def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        """打回阶段"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        issue.reject_stage(stage, reason)
        self._repo.save(issue)
        logger.info(f"Issue {issue_id} 阶段 {stage.value} 已打回: {reason}")
        return issue

    async def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        """手动触发 AI 执行"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return {"status": "error", "message": "Issue not found"}

        issue.start_stage(stage)
        self._repo.save(issue)

        # 触发执行
        return await self._executor.execute_stage(issue, stage)

    def update_issue(self, issue_id: str, **kwargs) -> Issue | None:
        """更新 Issue"""
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        if "title" in kwargs:
            issue.title = kwargs["title"]
        if "description" in kwargs:
            issue.description = kwargs["description"]
        if "status" in kwargs:
            if kwargs["status"] == "archived":
                issue.status = IssueStatus.ARCHIVED
                issue.archived_at = datetime.now()
            elif kwargs["status"] == "discarded":
                issue.status = IssueStatus.DISCARDED
                issue.discarded_at = datetime.now()

        self._repo.save(issue)
        return issue

    def archive_issue(self, issue_id: str) -> Issue | None:
        """归档 Issue"""
        return self.update_issue(issue_id, status="archived")

    def discard_issue(self, issue_id: str) -> Issue | None:
        """废弃 Issue"""
        return self.update_issue(issue_id, status="discarded")

    def delete_issue(self, issue_id: str) -> bool:
        """删除 Issue"""
        return self._repo.delete(IssueId(issue_id))

    async def _advance_and_trigger(self, issue: Issue, current_stage: Stage) -> None:
        """进入下一阶段并触发 AI"""
        # 计算下一阶段
        stages = list(Stage)
        current_idx = stages.index(current_stage)

        # 如果不是最后一个阶段
        if current_idx < len(stages) - 1:
            next_stage = stages[current_idx + 1]
            issue.start_stage(next_stage)
            self._repo.save(issue)
            logger.info(f"Issue {issue.id} 进入阶段: {next_stage.value}")

            # 异步触发 AI（不等待完成）
            self._executor.execute_stage_async(issue, next_stage)
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .issue_service import IssueService
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/application/service/issue_service.py src/swallowloop/application/service/__init__.py
git commit -m "feat(application): 添加 IssueService"
```

---

## Task 7: 应用服务 - ExecutorService

**Files:**
- Create: `src/swallowloop/application/service/executor_service.py`
- Modify: `src/swallowloop/application/service/__init__.py`

- [ ] **Step 1: 创建 executor_service.py**

```python
"""Executor Service - AI 执行编排"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...infrastructure.agent.iflow import IFlowAgent
    from ...domain.repository import IssueRepository

from ...domain.model import Issue, Stage

logger = logging.getLogger(__name__)

# 系统指令目录
INSTRUCTIONS_DIR = Path.home() / ".swallowloop" / "instructions"


class ExecutorService:
    """AI 执行服务"""

    def __init__(self, iflow_agent: "IFlowAgent", repository: "IssueRepository"):
        self._agent = iflow_agent
        self._repo = repository
        self._running_tasks: dict[str, asyncio.Task] = {}

    def get_workspace_dir(self, project: str, issue_id: str) -> Path:
        """获取工作空间目录"""
        return Path.home() / ".swallowloop" / project / str(issue_id) / "stages"

    def get_stage_dir(self, project: str, issue_id: str, stage: Stage) -> Path:
        """获取阶段目录"""
        return self.get_workspace_dir(project, issue_id) / stage.value

    def prepare_stage_context(self, project: str, issue_id: str, stage: Stage, document: str) -> None:
        """准备阶段上下文"""
        stage_dir = self.get_stage_dir(project, issue_id, stage)
        stage_dir.mkdir(parents=True, exist_ok=True)

        # 读取指令文件
        instruction_file = INSTRUCTIONS_DIR / f"{stage.value}.md"
        instruction = ""
        if instruction_file.exists():
            instruction = instruction_file.read_text()

        # 生成 context.md
        context_path = stage_dir / "context.md"
        context_content = f"""# 阶段: {stage.value}

## 指令
{instruction}

## Issue 文档
{document}
"""
        context_path.write_text(context_content, encoding="utf-8")
        logger.debug(f"生成 context.md: {context_path}")

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """异步执行阶段"""
        project = "default"  # TODO: 从配置获取

        # 准备上下文
        stage_state = issue.get_stage_state(stage)
        self.prepare_stage_context(project, str(issue.id), stage, stage_state.document)

        # 在线程池中执行（避免阻塞事件循环）
        context_path = self.get_stage_dir(project, str(issue.id), stage) / "context.md"
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._agent.execute(
                instruction=str(INSTRUCTIONS_DIR / f"{stage.value}.md"),
                context=str(context_path),
            )
        )

        # 保存产出
        if result.get("success"):
            output_path = self.get_stage_dir(project, str(issue.id), stage) / "output.md"
            output_path.write_text(result.get("output", ""), encoding="utf-8")

            # 更新 document 字段并保存
            stage_state.document = result.get("output", "")
            self._repo.save(issue)

        return result

    def execute_stage_async(self, issue: Issue, stage: Stage) -> None:
        """异步执行阶段（非阻塞）"""
        task_key = f"{issue.id}_{stage.value}"
        if task_key in self._running_tasks:
            logger.warning(f"任务已在执行中: {task_key}")
            return

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.execute_stage(issue, stage))
        self._running_tasks[task_key] = task
        task.add_done_callback(lambda _: self._running_tasks.pop(task_key, None))
```

- [ ] **Step 2: 更新 __init__.py**

```python
from .executor_service import ExecutorService
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/application/service/executor_service.py src/swallowloop/application/service/__init__.py
git commit -m "feat(application): 添加 ExecutorService"
```

---

## Task 8: Web API - Dashboard 扩展

**Files:**
- Modify: `src/swallowloop/interfaces/web/dashboard.py`

- [ ] **Step 1: 修改 dashboard.py - 添加 Issue API 端点**

在 DashboardServer 类中添加以下端点：

```python
# 在 _setup_routes 方法中添加：

@app.get("/api/issues")
async def list_issues():
    """获取所有 Issue"""
    issues = self._issue_service.list_issues()
    return {"issues": [self._issue_to_dict(i) for i in issues]}

@app.get("/api/issues/{issue_id}")
async def get_issue(issue_id: str):
    """获取单个 Issue"""
    issue = self._issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": self._issue_to_dict(issue)}

@app.post("/api/issues")
async def create_issue(request: Request):
    """创建 Issue"""
    data = await request.json()
    issue = self._issue_service.create_issue(
        title=data["title"],
        description=data.get("description", ""),
    )
    return {"issue": self._issue_to_dict(issue)}, 201

@app.patch("/api/issues/{issue_id}")
async def update_issue(issue_id: str, request: Request):
    """更新 Issue（归档/废弃）"""
    data = await request.json()
    issue = self._issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    if "status" in data:
        if data["status"] == "archived":
            issue = self._issue_service.archive_issue(issue_id)
        elif data["status"] == "discarded":
            issue = self._issue_service.discard_issue(issue_id)

    return {"issue": self._issue_to_dict(issue)}

@app.delete("/api/issues/{issue_id}")
async def delete_issue(issue_id: str):
    """删除 Issue"""
    success = self._issue_service.delete_issue(issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found")
    return None

@app.post("/api/issues/{issue_id}/stages/{stage}/approve")
async def approve_stage(issue_id: str, stage: str, request: Request):
    """审批通过阶段"""
    data = await request.json()
    issue = self._issue_service.approve_stage(
        issue_id,
        Stage(stage),
        comment=data.get("comment", ""),
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": self._issue_to_dict(issue)}

@app.post("/api/issues/{issue_id}/stages/{stage}/reject")
async def reject_stage(issue_id: str, stage: str, request: Request):
    """打回阶段"""
    data = await request.json()
    issue = self._issue_service.reject_stage(
        issue_id,
        Stage(stage),
        reason=data["reason"],
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": self._issue_to_dict(issue)}

@app.post("/api/issues/{issue_id}/trigger")
async def trigger_issue(issue_id: str, request: Request):
    """手动触发 AI 执行"""
    data = await request.json()
    result = self._issue_service.trigger_ai(
        issue_id,
        Stage(data["stage"]),
    )
    return result
```

- [ ] **Step 2: 添加辅助方法**

```python
def _issue_to_dict(self, issue: Issue) -> dict:
    """Issue 转字典"""
    return {
        "id": str(issue.id),
        "title": issue.title,
        "description": issue.description,
        "status": issue.status.value,
        "currentStage": issue.current_stage.value,
        "createdAt": issue.created_at.isoformat(),
        "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
        "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
        "stages": {
            stage.value: {
                "stage": stage.value,
                "status": state.status.value,
                "document": state.document,
                "comments": [...],  # 序列化 comments
                "startedAt": state.started_at.isoformat() if state.started_at else None,
                "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                "todoList": [...],  # 序列化 todo_list
                "progress": state.progress,
                "executionState": state.execution_state.value if state.execution_state else None,
            }
            for stage, state in issue.stages.items()
        },
    }
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/interfaces/web/dashboard.py
git commit -m "feat(web): 扩展 Dashboard 添加 Issue API 端点"
```

---

## Task 9: 指令文件

**Files:**
- Create: `~/.swallowloop/instructions/` 下的 7 个 Markdown 文件

- [ ] **Step 1: 创建指令文件目录**

```bash
mkdir -p ~/.swallowloop/instructions
```

- [ ] **Step 2: brainstorm.md**

```markdown
# 头脑风暴阶段指令

## 目标
根据 Issue 描述，生成多个可行的解决方案。

## 输入
- Issue 描述：见 context.md 中的 Issue 文档部分

## 执行方式
1. 仔细阅读 Issue 描述
2. 分析需求的核心问题
3. 考虑 2-5 种不同的技术路径
4. 评估每种方案的优缺点

## 输出格式
```markdown
# 方案一：[方案名称]

## 核心思路
...

## 优点
- ...

## 缺点
- ...

---

# 方案二：...
```

## 输出要求
- 使用 Markdown 格式
- 方案数量：2-5 个
- 每个方案包含：名称、核心思路、优缺点
```

- [ ] **Step 3: planFormed.md**

```markdown
# 方案成型阶段指令

## 目标
根据头脑风暴阶段选定的方案，形成整体实现思路。

## 输入
- 上一阶段（头脑风暴）的产出：见 ../brainstorm/output.md
- 当前 Issue 文档：见 context.md

## 执行方式
1. 阅读上一阶段的产出
2. 确定具体的技术方案
3. 描述整体实现思路和步骤

## 输出格式
```markdown
# 实现计划

## 整体思路
...

## 实施步骤
1. ...
2. ...
3. ...

## 技术选型
- 框架/库：...
- 工具：...
```
```

- [ ] **Step 4: detailedDesign.md**

```markdown
# 详细设计阶段指令

## 目标
将方案成型阶段的整体思路细化为可执行的技术设计。

## 输入
- 上一阶段（方案成型）的产出：见 ../planFormed/output.md
- Issue 描述：见 context.md

## 输出格式
```markdown
# 详细设计

## 模块划分
...

## 数据结构
...

## API 设计（如适用）
...

## 关键算法
...
```
```

- [ ] **Step 5: taskSplit.md**

```markdown
# 任务拆分阶段指令

## 目标
将详细设计拆分为可执行的小任务。

## 输入
- 上一阶段（详细设计）的产出：见 ../detailedDesign/output.md

## 输出格式
```markdown
# 任务拆分

## TODO 列表
- [ ] 任务1：...
- [ ] 任务2：...
- [ ] 任务3：...

## 任务依赖
1. 任务1 → 任务2
2. 任务2 → 任务3
```
```

- [ ] **Step 6: execution.md**

```markdown
# 执行阶段指令

## 目标
按照任务拆分阶段的 TODO 列表逐步执行代码任务。

## 输入
- 任务拆分阶段的 TODO 列表：见 context.md
- 详细设计文档：见 ../detailedDesign/output.md

## 执行方式
循环执行每个 TODO：
1. 读取当前 TODO 内容
2. 执行代码修改
3. 完成后标记状态
4. 进入下一个 TODO

## 输出格式
```markdown
# 执行进度

## 当前任务
- [x] 任务1：完成
- [x] 任务2：完成
- [ ] 任务3：进行中
- [ ] 任务4：待开始
```
```

- [ ] **Step 7: updateDocs.md**

```markdown
# 更新文档阶段指令

## 目标
更新代码文档和编写总结报告。

## 输入
- 执行阶段的产出：见 ../execution/output.md
- 相关代码变更：见 context.md

## 输出格式
```markdown
# 总结报告

## 执行摘要
...

## 代码变更
...

## 文档更新
...
```
```

- [ ] **Step 8: submit.md**

```markdown
# 提交阶段指令

## 目标
创建 PR 并提交代码。

## 输入
- 更新文档阶段的产出：见 ../updateDocs/output.md
- 代码变更：见 context.md

## 执行方式
1. 确保所有代码变更已提交
2. 创建 PR 描述
3. 提交 PR

## 输出格式
```markdown
# PR 信息

## 标题
...

## 描述
...

## 链接
PR: ...
```
```

- [ ] **Step 9: 提交**

```bash
mkdir -p ~/.swallowloop/instructions
# 创建上述所有指令文件
```

---

## Task 10: WebSocket 执行日志

**Files:**
- Modify: `src/swallowloop/interfaces/web/dashboard.py`

- [ ] **Step 1: 添加 WebSocket 连接管理器**

在 `ConnectionManager` 类中添加：

```python
# 在 DashboardServer.__init__ 中添加
self._issue_connections: dict[str, list[WebSocket]] = defaultdict(list)

# 添加 WebSocket 端点
@app.websocket("/ws/execution/{issue_id}")
async def ws_execution(websocket: WebSocket, issue_id: str):
    await websocket.accept()
    self._issue_connections[issue_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 客户端可以发送 ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        self._issue_connections[issue_id].remove(websocket)
```

- [ ] **Step 2: 添加广播方法**

```python
async def broadcast_execution_log(self, issue_id: str, log: dict) -> None:
    """广播执行日志到指定 Issue 的所有连接"""
    for ws in self._issue_connections.get(issue_id, []):
        try:
            await ws.send_json(log)
        except Exception:
            pass
```

- [ ] **Step 3: 在 ExecutorService 中集成**

修改 `ExecutorService` 接收 `dashboard` 引用以发送日志：

```python
class ExecutorService:
    def __init__(self, iflow_agent, repository, dashboard=None):
        self._agent = iflow_agent
        self._repo = repository
        self._dashboard = dashboard
        # ...

    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        # ... 执行逻辑 ...

        # 发送日志
        if self._dashboard:
            await self._dashboard.broadcast_execution_log(
                str(issue.id),
                {"level": "info", "message": "开始执行...", "timestamp": datetime.now().isoformat()}
            )
```

- [ ] **Step 4: 提交**

```bash
git add src/swallowloop/interfaces/web/dashboard.py
git commit -m "feat(web): 添加 WebSocket 执行日志支持"
```

---

## Task 11: Dashboard 依赖注入

**Files:**
- Modify: `src/swallowloop/interfaces/web/dashboard.py`
- Modify: `src/swallowloop/interfaces/web/standalone.py`

- [ ] **Step 1: 更新 DashboardServer 初始化**

```python
class DashboardServer:
    def __init__(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        issue_repository: IssueRepository,
        iflow_agent: IFlowAgent,
        settings: Settings,
        port: int = 8080,
    ):
        # 现有初始化 ...
        self._issue_service = IssueService(
            repository=issue_repository,
            executor=ExecutorService(
                iflow_agent=iflow_agent,
                repository=issue_repository,
                dashboard=self,  # 传入 self 以便发送 WebSocket 日志
            )
        )
```

- [ ] **Step 2: 更新 standalone.py**

```python
def main():
    # ... 现有代码 ...

    # 初始化 Issue 相关组件
    issue_repo = JsonIssueRepository(
        project=settings.issue_project,
        data_dir=settings.work_dir,
    )
    iflow_agent = IFlowAgent(config=settings.get_llm_config())

    # 创建 Dashboard
    dashboard = DashboardServer(
        task_repository=task_repo,
        workspace_repository=workspace_repo,
        issue_repository=issue_repo,
        iflow_agent=iflow_agent,
        settings=settings,
        port=args.port,
    )
```

- [ ] **Step 3: 提交**

```bash
git add src/swallowloop/interfaces/web/dashboard.py src/swallowloop/interfaces/web/standalone.py
git commit -m "feat(web): 集成 IssueService 到 Dashboard"
```

---

## Task 12: 配置更新

**Files:**
- Modify: `src/swallowloop/infrastructure/config/settings.py`

- [ ] **Step 1: 添加 Issue 相关配置**

```python
# 在 Settings 类中添加：

# Issue 配置
issue_project: str = "default"  # 当前项目名
```

- [ ] **Step 2: 提交**

```bash
git add src/swallowloop/infrastructure/config/settings.py
git commit -m "feat(config): 添加 issue_project 配置"
```

---

## Task 13: 测试

**Files:**
- Create: `tests/test_issue_service.py`

- [ ] **Step 1: 编写测试**

```python
"""Issue Service 测试"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.domain.repository import IssueRepository
from swallowloop.application.service import IssueService


class MockRepository(IssueRepository):
    def __init__(self):
        self._issues = {}

    def get(self, issue_id: IssueId) -> Issue | None:
        return self._issues.get(str(issue_id))

    def save(self, issue: Issue) -> None:
        self._issues[str(issue.id)] = issue

    def list_all(self) -> list[Issue]:
        return list(self._issues.values())

    def list_active(self) -> list[Issue]:
        return [i for i in self._issues.values() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        return self._issues.pop(str(issue_id), None) is not None


class MockExecutor:
    def execute_stage(self, issue, stage):
        return {"status": "success", "output": "mock output"}

    def execute_stage_async(self, issue, stage):
        pass


def test_create_issue():
    repo = MockRepository()
    service = IssueService(repo, MockExecutor())

    issue = service.create_issue("测试 Issue", "测试描述")

    assert issue.title == "测试 Issue"
    assert issue.status == IssueStatus.ACTIVE
    assert issue.current_stage == Stage.BRAINSTORM


def test_approve_stage():
    repo = MockRepository()
    service = IssueService(repo, MockExecutor())

    issue = service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 审批通过头脑风暴阶段
    updated = service.approve_stage(issue_id, Stage.BRAINSTORM, "通过")

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED
    # 应该自动进入下一阶段
    assert updated.current_stage == Stage.PLAN_FORMED


def test_reject_stage():
    repo = MockRepository()
    service = IssueService(repo, MockExecutor())

    issue = service.create_issue("测试 Issue", "测试描述")
    issue_id = str(issue.id)

    # 打回头脑风暴阶段
    updated = service.reject_stage(issue_id, Stage.BRAINSTORM, "方案不够详细")

    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.REJECTED
    # 最新评论应该是 reject
    comments = updated.get_stage_state(Stage.BRAINSTORM).comments
    assert comments[-1].action == "reject"
    assert comments[-1].content == "方案不够详细"
```

- [ ] **Step 2: 运行测试**

```bash
pytest tests/test_issue_service.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_issue_service.py
git commit -m "test: 添加 IssueService 单元测试"
```

---

## 执行顺序

1. Task 1: 领域模型 - Stage 枚举和值对象
2. Task 2: 领域模型 - Comment 值对象
3. Task 3: 领域模型 - Issue 聚合根
4. Task 4: 仓库接口 - IssueRepository
5. Task 5: 持久化 - JsonIssueRepository
6. Task 6: 应用服务 - IssueService
7. Task 7: 应用服务 - ExecutorService
8. Task 8: Web API - Dashboard 扩展
9. Task 9: 指令文件
10. Task 10: WebSocket 执行日志
11. Task 11: Dashboard 依赖注入
12. Task 12: 配置更新
13. Task 13: 测试
