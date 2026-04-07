# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SwallowLoop（燕子回环）是一个围绕代码仓库的智能维护 Agent 系统。通过监听 GitHub Issue 并自动生成 PR 来完成代码任务。

## 开发命令

```bash
# 使用 run.sh 管理服务（必须使用）
./run.sh -backend     # 启动后端
./run.sh -frontend    # 启动前端
./run.sh              # 启动全部（后端+前端）
./run.sh stop         # 停止全部
./run.sh stop -backend # 停止后端
./run.sh restart      # 重启全部
./run.sh status       # 查看状态
./run.sh test         # 运行测试（后端+前端）

# 直接运行（仅开发调试用）
uv run swallowloop

# 运行测试（仅后端单元测试）
pytest tests/ -v

# 运行单个测试文件
pytest tests/module/agent/test_deerflow_agent.py -v

# 运行单个测试函数
pytest tests/module/config/test_config.py::TestConfigLoad::test_load_yaml_file -v
```

**重要**：优先使用 `run.sh` 管理服务，如果脚本有问题必须优先修复。

## 文档索引

| 文档 | 说明 |
|------|------|
| `docs/architecture.md` | 系统架构、数据流、模块职责 |
| `docs/CODING_STANDARDS.md` | **代码规范**（命名、Git、测试、禁止事项） |
| `docs/GLOSSARY.md` | **术语表**（核心概念、状态机流转） |
| `docs/data_models.md` | 数据模型详细定义 |
| `docs/vision.md` | 项目愿景和设计思想 |
| `docs/lessons/` | 经验教训（问题复盘和解决方案） |

## 架构

采用 DDD 分层架构：

```
src/swallowloop/
├── domain/              # 领域层（零依赖）
│   ├── model/          # 领域模型
│   ├── repository/     # 仓库接口
│   ├── statemachine/   # 状态机
│   └── event/          # 领域事件
├── application/         # 应用层（依赖 domain）
│   ├── dto/           # 数据传输对象
│   └── service/        # 应用服务
├── infrastructure/     # 基础设施层（依赖 domain 接口）
│   ├── persistence/    # 持久化
│   ├── executor/       # 执行器
│   ├── agent/          # AI Agent
│   ├── config/         # 配置
│   ├── llm/           # 大模型配置
│   ├── logging/        # 日志
│   └── self_update/    # 自更新
└── interfaces/          # 接口层（依赖 application）
    └── web/            # Web API
```

### 接口规范

**修改代码前必须加载 `architecture-design` 技能**，确保遵守：
- 依赖方向规范（只能从外层指向内层）
- 接口约束（调用方只依赖抽象接口）
- 禁止事项（asyncio.run 在同步函数内等）

**运行契约检查**：
```bash
python .claude/skills/architecture-design/scripts/check_contracts.py
```

**架构设计技能**：使用 `architecture-design` skill 获取接口规范、依赖方向、契约检查和自检机制。详细说明见 `.claude/skills/architecture-design/SKILL.md`。

**修改检查清单**：
- [ ] 改动的代码在哪个模块？
- [ ] 这个模块的接口是谁？调用方是谁？
- [ ] 会不会破坏依赖方向？
- [ ] 需不需要同步修改调用方？
- [ ] 测试能发现这个问题吗？

### 模块命名规则

**所有模块必须在 `__init__.py` 中定义 `MODULE_NAME` 常量**：

```python
# 层级模块
MODULE_NAME = "domain"

# 子模块（层级.子模块）
MODULE_NAME = "domain.model"
MODULE_NAME = "infrastructure.persistence"
```

**规则**：
1. 每个有 `__init__.py` 的目录都是一个模块
2. 模块必须定义 `MODULE_NAME = "x.y.z"` 常量
3. `__all__` 列表中必须包含 `"MODULE_NAME"`
4. **新增模块必须经过开发者确认**，不能自行创建

## Agent 系统

两种 Agent 类型，通过 `AGENT_TYPE` 配置：
- `mock`: 模拟 Agent（用于测试环境，固定延迟 5 秒）
- `deerflow`: 使用 DeerFlow 2.0（通过 HTTP API 与 DeerFlow 通信）

DeerFlow Agent 通过 HTTP API 与独立部署的 DeerFlow 通信，每个 Issue 对应一个 Thread。

## 多仓库支持

支持多仓库监听，通过 `REPOS` 配置（逗号分隔，格式 `owner/repo`）。

## LLM 配置

LLM 配置与 Agent 类型独立，支持通过 `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL_NAME` 环境变量配置。

## 关键设计

1. **Worker 线程池**: 使用 `ThreadPoolExecutor` 执行异步任务
2. **并发控制**: ExecutorWorkerPool 控制最大 Worker 数量
3. **资源清理**: 任务完成后自动删除本地工作空间和远端分支
4. **持久化**: 使用内存存储，线程安全

## Git Workflow

- Always confirm before running git push operations - show pending commits first
- **提交代码前必须确保 `pytest tests/ -v` 全部通过**

## 前后端代码改动验证规范

当代码改动**涉及前端或后端 API 接口**时（包括但不限于）：
- 修改了 API 响应格式
- 新增/修改了前端组件
- 修改了状态机或业务流程

**必须执行 E2E 验证流程**：

1. **启动完整环境**（后端+前端）：
   ```bash
   ./run.sh
   ```

2. **使用浏览器验证**（使用 chrome-devtools MCP 工具）：
   - 访问 http://localhost:9501/
   - 验证看板正确显示（新建/进行中/已完成 三列）
   - 创建 Issue 验证完整流程
   - 点击 Issue 卡片验证 Pipeline 详情 Tab 正确显示

3. **API 验证**（确保后端 API 正确）：
   ```bash
   # 创建 Issue
   curl -X POST http://localhost:9501/api/issues \
     -H "Content-Type: application/json" \
     -d '{"title":"测试","description":"描述"}'

   # 触发 AI 执行
   curl -X POST "http://localhost:9501/api/issues/{issue_id}/trigger" \
     -H "Content-Type: application/json" \
     -d '{"stage":"environment"}'

   # 验证状态
   curl http://localhost:9501/api/issues/{issue_id} \
     | python3 -c "import sys,json; d=json.load(sys.stdin); ..."
   ```

4. **关键验证点**：
   - [ ] `runningStatus` 正确转换（new → in_progress → done）
   - [ ] `pipeline` 信息包含完整的 stage/task 状态
   - [ ] 前端看板正确分组显示

## Configuration

- When I mention a setting, always show me the exact file path and current value before making changes
- Before editing any config file, say: "Your current [setting name] in [file path] is [value]. I'll change it to [new value]. OK?"

## Working with URLs

- Before attempting browser/URL access, ask if I want to use web_search or WebFetch tools
- If my requested method isn't possible, say: "I can't do [X], but I can [alternative approach]. Want me to try that?"

## 经验教训

项目经验教训存放在 `docs/lessons/` 目录。

**重要原则**：发现问题并解决后，必须反思为什么测试用例没有发现，并将根因分析记录到经验目录。

参考：`docs/lessons/README.md`
