# 功能规范：SDD 阶段流水线重构

**Feature Branch**: `001-sdd-stage-migration`
**Created**: 2026-04-07
**Status**: Draft
**Input**: "保留现在的环境准备阶段，我想将后续的阶段变成sdd的几个阶段"

## Clarifications

### Session 2026-04-07

- Q: 阶段超时处理策略 → A: 标记阶段为"失败"，用户可手动重试
- Q: 打回后 DeerFlow 重新执行还是暂停 → A: 自动重新执行一次，仍失败则停止
- Q: 多个 Issue 并发执行时 DeerFlow 如何处理 → A: DeerFlow 一次执行一个任务，其他 Issue 排队
- Q: 阶段执行结果的存储位置 → A: 存储在 Issue 的 stages[stageName].stage_content 字段
- Q: 审批意见是否必须填写 → A: 通过可选，打回必填意见

## 用户场景与测试

### 用户故事 1 - DeerFlow 自动执行流水线 (Priority: P1)

作为开发者，我希望在 Web 界面触发流水线后，系统自动将任务下发给 DeerFlow 执行，DeerFlow 完成每个阶段后自动进入下一阶段，我只在关键节点审批。

**为什么这个优先级**：这是核心功能，决定了人机协作的效率。

**独立测试**：可以通过 Web 界面触发 Issue 流水线，观察 DeerFlow 执行并验证阶段自动流转。

**验收场景**：

1. **Given** Issue 已创建并完成环境准备，**When** 用户点击"触发 AI"按钮，**Then** 系统自动将规范定义任务下发给 DeerFlow
2. **Given** DeerFlow 执行完规范定义阶段，**When** 用户审批通过，**Then** 系统自动将需求澄清任务下发给 DeerFlow
3. **Given** DeerFlow 完成需求澄清，**When** 用户审批通过，**Then** 系统自动将技术规划任务下发给 DeerFlow
4. **Given** DeerFlow 执行完技术规划，**When** 用户审批通过，**Then** 系统自动将质量检查任务下发给 DeerFlow
5. **Given** DeerFlow 完成质量检查，**When** 用户审批通过，**Then** 系统自动将任务拆分任务下发给 DeerFlow
6. **Given** DeerFlow 完成任务拆分，**When** 用户审批通过，**Then** 系统自动将一致性分析任务下发给 DeerFlow
7. **Given** DeerFlow 完成一致性分析，**When** 用户审批通过，**Then** 系统自动将编码实现任务下发给 DeerFlow
8. **Given** DeerFlow 完成编码实现，**When** 用户审批通过，**Then** 系统自动创建 PR

---

### 用户故事 2 - 阶段状态追踪 (Priority: P2)

作为开发者，我希望在 Web 界面看到每个阶段的清晰状态（等待中、执行中、已完成、已审批），便于了解进度。

**为什么这个优先级**：提高透明性，帮助用户了解当前进度和 DeerFlow 工作状态。

**独立测试**：可以通过 Web 界面查看 Issue 详情并验证状态显示来验证。

**验收场景**：

1. **Given** Issue 在执行中，**When** 用户打开 Issue 详情，**Then** 显示当前阶段和所有历史阶段的状态
2. **Given** 阶段正在执行，**When** DeerFlow 完成后，**Then** 状态自动更新为"待审批"
3. **Given** 用户审批阶段，**When** 点击"通过"或"打回"，**Then** 状态更新并触发下一阶段

---

### 边界情况

- 当 DeerFlow 执行超时时：标记阶段为"失败"，用户可手动重试
- 当用户打回阶段时：自动重新执行一次，仍失败则停止
- 当 DeerFlow 执行失败时：自动重试一次，仍失败则标记失败
- 多个 Issue 同时执行时：DeerFlow 一次执行一个任务，其他 Issue 排队
- 审批意见：通过时意见可选，打回时意见必填

## 功能需求

### 功能性需求

- **FR-001**: 系统必须保留现有的环境准备阶段（创建workspace、clone代码）
- **FR-002**: 系统必须实现 SDD 阶段流水线（9个阶段）
- **FR-003**: 每个阶段必须支持下发给 DeerFlow 执行
- **FR-004**: DeerFlow 完成后系统必须自动更新阶段状态
- **FR-005**: 每个阶段必须支持人类审批才能进入下一阶段
- **FR-006**: 阶段状态变更必须记录时间戳和操作历史
- **FR-007**: Web 界面必须实时显示 DeerFlow 执行状态

### 关键实体

- **PipelineStage**: 流水线阶段，包含名称、DeerFlow 任务描述、状态、顺序
- **StageExecution**: 阶段执行记录，包含 DeerFlow run_id、执行状态、开始时间、完成时间
- **StageTransition**: 阶段转换记录，包含从哪个阶段到哪个阶段、时间戳、操作人

## 成功标准

### 可衡量指标

- **SC-001**: DeerFlow 执行单个阶段的时间不超过 30 分钟
- **SC-002**: 阶段状态在 DeerFlow 完成后 5 秒内更新
- **SC-003**: 用户可以在 Web 界面看到 DeerFlow 实时的执行进度
- **SC-004**: 开发者完成一个完整 Issue 的人工审批时间不超过 2 小时

## 假设

- DeerFlow Agent 服务正常运行
- 环境准备阶段的工作流程保持不变
- spec-kit 相关命令已在 DeerFlow 环境中可用
- DeerFlow 支持通过 API 接收任务并返回执行结果
