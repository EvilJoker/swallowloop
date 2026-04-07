# Implementation Plan: SDD 阶段流水线重构

**Branch**: `001-sdd-stage-migration` | **Date**: 2026-04-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-sdd-stage-migration/spec.md`

## Summary

将现有流水线重构为 SDD（Spec-Driven Development）阶段流水线，集成 DeerFlow Agent 实现自动化执行与人类审批的混合控制流。核心变更：保留环境准备阶段，将后续阶段改为规范定义→需求澄清→技术规划→质量检查→任务拆分→一致性分析→编码实现→提交发布的 8 阶段流程，每个阶段通过 DeerFlow 执行，完成后进入待审批状态，人类审批后进入下一阶段。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, httpx, DeerFlow Agent (HTTP API)
**Storage**: 内存存储（Issue 模型 + PipelineContext）
**Testing**: pytest + 浏览器 E2E 验证
**Target Platform**: Linux server (Docker)
**Project Type**: Web 服务 + AI Agent 调度系统
**Performance Goals**: DeerFlow 单阶段执行 ≤30 分钟，状态更新 ≤5 秒
**Constraints**: DeerFlow 一次执行一个任务，其他排队
**Scale/Scope**: 单仓库多 Issue 并发（各 Issue 独立 Pipeline）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 检查项 | 状态 |
|------|--------|------|
| I. 人类决策权 | 每个阶段需人类审批才能进入下一阶段 | ✅ 通过 - Stage.approval_state 字段支持 |
| I. 人类决策权 | 打回必须包含反馈意见 | ✅ 通过 - reject() 方法需填写 reason |
| II. 流水线透明性 | AI 产出存为 Markdown，标明来源 | ✅ 通过 - stage_content 字段存储 JSON/Markdown |
| II. 流水线透明性 | 阶段转换记录时间戳和操作历史 | ✅ 通过 - StageTransition 日志记录 |
| III. 测试优先原则 | 功能修改包含对应测试 | ✅ 通过 - 每个阶段需单元测试 |
| IV. DDD 架构合规性 | Domain 层不依赖外层 | ✅ 通过 - Stage/Task 在 domain 层 |
| IV. DDD 架构合规性 | Infrastructure 只依赖 Domain 接口 | ✅ 通过 - DeerFlowAgent 实现 BaseAgent |
| V. 最小化接口原则 | 模块暴露必要方法 | ✅ 通过 - Pipeline 暴露 5 个核心方法 |

**Gate 结果**: 全部通过，无需 justify

## Project Structure

### Documentation (this feature)

```text
specs/001-sdd-stage-migration/
├── plan.md              # 本文件
├── research.md          # Phase 0 - 调研输出（本次创建）
├── data-model.md        # Phase 1 - 数据模型（本次创建）
├── quickstart.md        # Phase 1 - 快速入门（本次创建）
└── contracts/           # Phase 1 - 接口契约（本次创建）
    └── sdd-stage-contract.md
```

### Source Code (repository root)

```text
src/swallowloop/
├── domain/pipeline/              # Pipeline 领域层（核心变更）
│   ├── stage.py                  # Stage 基类（新增 approval_state 字段）
│   ├── task.py                   # Task 基类（支持异步 handler）
│   ├── context.py                # PipelineContext
│   ├── issue_pipeline.py         # IssuePipeline（SDD 9 阶段）
│   ├── environment_stage/        # 环境准备阶段（保留）
│   ├── specify_stage/           # 规范定义阶段
│   ├── clarify_stage/            # 需求澄清阶段
│   ├── plan_stage/              # 技术规划阶段
│   ├── checklist_stage/         # 质量检查阶段
│   ├── tasks_stage/             # 任务拆分阶段
│   ├── analyze_stage/            # 一致性分析阶段
│   ├── implement_stage/          # 编码实现阶段
│   └── submit_stage/            # 提交发布阶段
└── application/service/          # 应用层
    └── executor_service.py       # 执行器服务（修改以适配新流程）
```

**Structure Decision**: 复用现有 DDD 分层结构，在 `domain/pipeline/` 下新增/重组阶段类。

### SDD 阶段列表

| 阶段名称 | 说明 | 目录 |
|---------|------|------|
| environment | 环境准备 | environment_stage/ |
| specify | 规范定义 | specify_stage/ |
| clarify | 需求澄清 | clarify_stage/ |
| plan | 技术规划 | plan_stage/ |
| checklist | 质量检查 | checklist_stage/ |
| tasks | 任务拆分 | tasks_stage/ |
| analyze | 一致性分析 | analyze_stage/ |
| implement | 编码实现 | implement_stage/ |
| submit | 提交发布 | submit_stage/ |

## Complexity Tracking

无 Constitution 违规，无需复杂度过 tracking。

## Research

### 调研结论

**DeerFlow Agent 接口**：
- `BaseAgent.execute(task_message, context)` - 异步执行任务
- 返回 `AgentResult(success, output, error)`
- 通过 HTTP API 与 DeerFlow 通信（默认 `http://localhost:2026`）

**现有 Pipeline 架构**：
- `Stage` 基类包含 `name`, `tasks[]`, `status`
- `Task` 基类包含 `handler`, `execute()` 方法
- `IssuePipeline` 包含所有 Stage，按顺序执行

**阶段指令存储**：
- `STAGE_INSTRUCTIONS` 字典存储各阶段指令文本
- 阶段执行时注入到 task_message

### 未知项与解决方案

| 未知项 | 解决方案 |
|--------|----------|
| 新阶段 (clarify, checklist, analyze) 的具体 Task 设计 | 参考现有 Task 模式，为每个阶段创建专门 Task |
| stage_content 存储格式 | 统一存储为 JSON 字符串，UI 层负责渲染 |
