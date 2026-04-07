# SwallowLoop 术语表

## 一、核心概念

### Issue（议题）
| 属性 | 说明 |
|------|------|
| 定义 | SwallowLoop 的工作单元，对应一个需要解决的技术任务 |
| 生命周期 | NEW → ACTIVE → ARCHIVED/DISCARDED |
| 聚合根 | 是，包含所有子状态 |

### Stage（阶段）
| 属性 | 说明 |
|------|------|
| 定义 | Issue 处理流水线中的一个步骤 |
| 数量 | 7 个阶段 |
| 流转 | 必须按顺序经过，审批通过才能进入下一阶段 |

### StageStatus（阶段状态）
| 状态 | 值 | 说明 |
|-----|-----|------|
| NEW | `new` | 新建，等待触发 |
| RUNNING | `running` | 执行中 |
| PENDING | `pending` | 待审批 |
| APPROVED | `approved` | 已通过 |
| REJECTED | `rejected` | 已打回 |
| ERROR | `error` | 异常 |

### Pipeline（流水线）
| 属性 | 说明 |
|------|------|
| 定义 | Stage 的集合，包含执行逻辑 |
| 环境准备 | ENVIRONMENT 阶段使用 Pipeline 执行任务 |

---

## 二、7 阶段定义

| 阶段 | 枚举值 | 说明 | AI 产出 | 人类操作 |
|-----|--------|------|---------|---------|
| **环境准备** | `environment` | 初始化工作环境 | 工作空间、代码库 | 监控 |
| **头脑风暴** | `brainstorm` | 探索多种可行方案 | Markdown 方案列表 | 选择方案 |
| **方案成型** | `planFormed` | 确定整体实现思路 | 架构设计 | 审核 |
| **详细设计** | `detailedDesign` | 精细化技术设计 | 详细文档 | 审核 |
| **任务拆分** | `taskSplit` | 拆解为可执行任务 | TODO 列表 | 审核 |
| **执行** | `execution` | 实施代码变更 | 代码变更 | 监控 |
| **更新文档** | `updateDocs` | 总结产出 | 总结报告 | 查看 |
| **提交** | `submit` | 创建 PR | Pull Request | 最终审核 |

---

## 三、泳道图概念

### IssueRunningStatus（泳道状态）
| 状态 | 值 | 说明 |
|-----|-----|------|
| NEW | `new` | 新建，未开始处理 |
| IN_PROGRESS | `in_progress` | 处理中，Pipeline 执行中 |
| DONE | `done` | 已完成 |

### 泳道图布局
```
┌─────────────┬─────────────┬─────────────┐
│    新建     │   进行中    │   已完成    │
│   (new)    │(in_progress)│   (done)   │
└─────────────┴─────────────┴─────────────┘
```

---

## 四、Task 和 Todo

### Task（Pipeline 任务）
| 属性 | 说明 |
|------|------|
| 定义 | Pipeline 中的原子执行单元 |
| 执行方式 | 按顺序执行，失败停止 |

### TodoItem（待办项）
| 属性 | 说明 |
|------|------|
| 定义 | 执行阶段的任务清单 |
| 状态 | PENDING → IN_PROGRESS → COMPLETED/FAILED |

### TodoStatus
| 状态 | 值 | 说明 |
|-----|-----|------|
| PENDING | `pending` | 待执行 |
| IN_PROGRESS | `in_progress` | 执行中 |
| COMPLETED | `completed` | 已完成 |
| FAILED | `failed` | 失败 |

---

## 五、Agent 相关

### Agent（智能体）
| 属性 | 说明 |
|------|------|
| 定义 | 与 DeerFlow 交互执行 AI 任务的组件 |
| 类型 | DeerFlowAgent（真实） |

### Thread（DeerFlow 线程）
| 属性 | 说明 |
|------|------|
| 定义 | DeerFlow 中的会话单元 |
| 生命周期 | prepare() 创建 → execute() 执行 → cleanup() 清理 |

### Workspace（工作空间）
| 属性 | 说明 |
|------|------|
| 定义 | Thread 对应的本地文件系统目录 |
| 路径格式 | `~/.deer-flow/threads/{thread_id}/user-data/workspace/` |

---

## 六、API 和接口

### IExecutor（执行器接口）
```python
class IExecutor(ABC):
    @abstractmethod
    async def prepare_workspace(self, issue: Issue, stage: Stage) -> bool:
        """准备工作空间"""
        pass

    @abstractmethod
    async def execute_stage(self, issue: Issue, stage: Stage) -> dict:
        """执行阶段"""
        pass
```

### BaseAgent（Agent 基类）
```python
class BaseAgent(ABC):
    @abstractmethod
    async def prepare(self, issue_id: str, context: dict) -> Workspace:
        """创建 Thread"""
        pass

    @abstractmethod
    async def execute(self, task: str, context: dict) -> AgentResult:
        """执行任务"""
        pass
```

---

## 七、持久化和状态

### IssueRepository（仓储接口）
```python
class IssueRepository(ABC):
    @abstractmethod
    def save(self, issue: Issue) -> None:
        pass

    @abstractmethod
    def get(self, issue_id: IssueId) -> Issue | None:
        pass
```

### InMemoryIssueRepository
| 属性 | 说明 |
|------|------|
| 定义 | 内存实现的仓储 |
| 线程安全 | 是（使用 threading.Lock） |
| 用途 | 开发测试、单实例运行 |

---

## 八、配置相关

### Config（配置单例）
| 方法 | 说明 |
|------|------|
| `get_github_repos()` | 获取仓库列表 |
| `get_agent_type()` | 获取 Agent 类型 |
| `get_deerflow_base_url()` | 获取 DeerFlow 地址 |
| `get_llm_config()` | 获取 LLM 配置 |
| `get_work_dir()` | 获取工作目录 |

### LLM 配置结构
```python
{
    "provider": "minimax",
    "api_key": "xxx",
    "base_url": "https://api.minimaxi.com/v1",
    "model_name": "m2.7"
}
```

---

## 九、缩写对照

| 缩写 | 全称 | 中文 |
|------|------|------|
| Issue | Issue | 议题/工单 |
| PR | Pull Request | 拉取请求 |
| LLM | Large Language Model | 大语言模型 |
| API | Application Programming Interface | 应用程序接口 |
| ABC | Abstract Base Class | 抽象基类 |
| DTO | Data Transfer Object | 数据传输对象 |
| DDD | Domain-Driven Design | 领域驱动设计 |

---

## 十、文件路径约定

| 路径 | 说明 |
|------|------|
| `~/.swallowloop/` | 用户数据根目录 |
| `~/.swallowloop/.env` | 用户配置文件 |
| `~/.swallowloop/config.yaml` | 业务配置文件 |
| `~/.deer-flow/` | DeerFlow 数据目录 |
| `~/.deer-flow/threads/{thread_id}/` | Thread 数据 |
| `src/swallowloop/` | 源代码根目录 |
| `tests/` | 测试目录 |

---

## 十一、状态机流转图

### 单阶段状态流转
```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
    NEW ──► RUNNING ──► PENDING ──► APPROVED      │
         │         │          │                   │
         │         │          ▼                   │
         │         │       REJECTED ──► RUNNING  │
         │         │          │                   │
         │         ▼          │                   │
         └─────► ERROR ◄─────┘                   │
                       │                          │
                       └──────────────────────────┘
```

### Issue 生命周期
```
NEW ──► ACTIVE ──► ARCHIVED
              │
              └────► DISCARDED
```
