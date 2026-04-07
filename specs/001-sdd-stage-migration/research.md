# Research: SDD 阶段流水线重构

**Branch**: `001-sdd-stage-migration` | **Date**: 2026-04-07

## 决策总结

### 1. DeerFlow Agent 接口

**决策**: 使用现有 `BaseAgent.execute()` 接口

**理由**:
- 接口已实现异步执行
- 返回结构化 `AgentResult`
- 支持 thread_id 上下文隔离

**备选方案**:
- 直接调用 DeerFlow HTTP API → 放弃，已封装在 BaseAgent 中

### 2. 阶段 Task 设计

**决策**: 每个 SDD 阶段一个 Task 类

**理由**:
- 符合现有 Stage/Task 架构
- 便于独立测试
- 清晰的关注点分离

**备选方案**:
- 单一 Task 处理所有阶段 → 放弃，违背最小化接口原则

### 3. 阶段指令管理

**决策**: 各阶段 Task 内部包含指令模板

**理由**:
- 指令与 Task 逻辑紧耦合
- 便于版本管理
- 符合 DDD 原则（领域知识内聚）

**备选方案**:
- 集中存储在 STAGE_INSTRUCTIONS 字典 → 放弃，维护成本高

### 4. 阶段结果存储

**决策**: 存储在 `issue.stages[stageName].stage_content`

**理由**:
- 符合 spec 定义
- Issue 模型已支持
- 便于前端展示

## 关键发现

### DeerFlow Agent 特性

- `execute()` 返回 `AgentResult(success, output, error)`
- 支持 `thread_id` 隔离不同 Issue 的执行
- 超时由 `MAX_EXECUTE_TIMEOUT_SECONDS` 控制（默认 30 分钟）

### Pipeline 状态机

- `StageState`: PENDING → RUNNING → COMPLETED/FAILED
- `StageStatus`: 包含 state, reason, timestamp
- 阶段执行后需要人类审批才能进入下一阶段

## 外部依赖

- DeerFlow 服务必须正常运行
- DeerFlow 环境中需包含 spec-kit 相关命令

## 开放问题

无