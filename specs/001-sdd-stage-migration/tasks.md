# Tasks: SDD 阶段流水线重构

**Input**: Design documents from `/specs/001-sdd-stage-migration/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 归属的用户故事（如 US1）

## SDD 阶段列表

| 阶段 | 说明 | 目录 |
|------|------|------|
| environment | 环境准备 | environment_stage/ |
| specify | 规范定义 | specify_stage/ |
| clarify | 需求澄清 | clarify_stage/ |
| plan | 技术规划 | plan_stage/ |
| checklist | 质量检查 | checklist_stage/ |
| tasks | 任务拆分 | tasks_stage/ |
| analyze | 一致性分析 | analyze_stage/ |
| implement | 编码实现 | implement_stage/ |
| submit | 提交发布 | submit_stage/ |

---

## Phase 1: 基础设施（Setup）

**Purpose**: 项目初始化和基础结构搭建

### 基础设施任务

- [x] T001 [P] 创建 Stage 基类，新增 `approval_state`, `approved_at`, `approver_comments` 字段 - `src/swallowloop/domain/pipeline/stage.py`
- [x] T002 [P] 创建 Task 基类，支持异步 handler（检测 iscoroutinefunction 并使用事件循环执行） - `src/swallowloop/domain/pipeline/task.py`
- [x] T003 [P] 新增 `ApprovalState` 枚举类 - `src/swallowloop/domain/pipeline/stage.py`
- [x] T004 [P] 新增 `StageState` 枚举（WAITING_APPROVAL 等） - `src/swallowloop/domain/pipeline/stage.py`

---

## Phase 2: 核心测试（Foundational - 测试优先）

**Purpose**: 先写测试，驱动实现

### 单元测试

- [x] T005 [P] 单元测试：Stage.approval_state 状态转换 - `tests/module/pipeline/test_approval.py`
- [x] T006 [P] 单元测试：Task 异步 handler 执行 - `tests/module/pipeline/test_task_async.py`
- [x] T007 [P] 单元测试：IssuePipeline.approve_stage() 审批逻辑 - `tests/module/pipeline/test_issue_pipeline_approval.py`

### 集成测试

- [x] T008 [P] 集成测试：完整流水线状态转换 - `tests/module/pipeline/test_pipeline_integration.py`
- [x] T009 [P] 集成测试：打回后自动重试逻辑验证 - `tests/module/pipeline/test_pipeline_integration.py`

**Checkpoint**: 测试就绪，可以驱动实现

---

## Phase 3: Pipeline 核心实现（Foundational）

**Purpose**: 核心基础设施，所有用户故事依赖于此

### Pipeline 核心重构

- [x] T010 [P] [US1] 重构 IssuePipeline，实现 SDD 9 阶段列表 - `src/swallowloop/domain/pipeline/issue_pipeline.py`
- [x] T011 [P] [US1] 实现 `execute_stage()` 方法，调用 DeerFlow Agent 执行任务 - SDD Stage Tasks 异步 handler
- [x] T012 [P] [US1] 实现 `approve_stage()` 方法，处理审批逻辑（通过/打回）- `IssueService`
- [x] T013 [P] [US1] 实现自动进入下一阶段的逻辑（approve 后设置下一阶段为 PENDING）- `_advance_to_next_stage()`
- [x] T014 [P] [US1] 实现审批日志记录（时间戳、操作人、审批意见）- `Stage.approve()/reject()` + `ReviewComment`

### ExecutorService 修改

- [x] T015 [P] [US1] 修改 `execute_stage()` 以处理 WAITING_APPROVAL 状态 - `issue_pipeline.execute_stage()` 调用 `set_waiting_approval()`
- [x] T016 [P] [US1] 实现 `approve_stage()` API 端点 - `src/swallowloop/interfaces/web/api/issues.py`
- [ ] T017 [P] [US1] 实现打回后的自动重试逻辑（REJECTED → 重新执行一次 → 仍失败则停止）

### E2E 测试

- [ ] T018 [P] E2E 测试：完整流水线触发 → DeerFlow 执行 → 审批 → 进入下一阶段

**Checkpoint**: Foundational 完成 - 用户故事可以开始并行开发

---

## Phase 4: User Story 1 - SDD 阶段 Task 创建（Priority: P1）

**Goal**: Web 界面触发流水线后，系统自动将任务下发给 DeerFlow 执行，完成后进入待审批状态，人类审批后进入下一阶段

**Independent Test**: 通过 Web 界面触发 Issue 流水线，观察 DeerFlow 执行并验证阶段自动流转

### SDD 阶段 Task 创建

- [x] T019 [P] [US1] 创建 SpecifyStage + SpecifyTask（规范定义）- `src/swallowloop/domain/pipeline/specify_stage/specify_stage.py`
- [x] T020 [P] [US1] 创建 ClarifyStage + ClarifyTask（需求澄清）- `src/swallowloop/domain/pipeline/clarify_stage/clarify_stage.py`
- [x] T021 [P] [US1] 创建 PlanStage + PlanTask（技术规划）- `src/swallowloop/domain/pipeline/plan_stage/plan_stage.py`
- [x] T022 [P] [US1] 创建 ChecklistStage + ChecklistTask（质量检查）- `src/swallowloop/domain/pipeline/checklist_stage/checklist_stage.py`
- [x] T023 [P] [US1] 创建 TasksStage + TasksTask（任务拆分）- `src/swallowloop/domain/pipeline/tasks_stage/tasks_stage.py`
- [x] T024 [P] [US1] 创建 AnalyzeStage + AnalyzeTask（一致性分析）- `src/swallowloop/domain/pipeline/analyze_stage/analyze_stage.py`
- [x] T025 [P] [US1] 创建 ImplementStage + ImplementTask（编码实现）- `src/swallowloop/domain/pipeline/implement_stage/implement_stage.py`
- [x] T026 [P] [US1] 适配 SubmitStage（提交发布）- `src/swallowloop/domain/pipeline/submit_stage/submit_stage.py`

**Checkpoint**: SDD 9 阶段全部就绪

---

## Phase 5: User Story 1 - 前端审批 UI（Priority: P1）

**Goal**: 提供人类审批界面

### 前端审批组件

- [ ] T027 [P] [US1] 添加阶段审批按钮（通过/打回）- `src/swallowloop/interfaces/web/src/components/PipelineApproval.vue`
- [ ] T028 [P] [US1] 添加审批意见输入框（打回时必填）- `src/swallowloop/interfaces/web/src/components/PipelineApproval.vue`
- [ ] T029 [P] [US1] 显示阶段执行结果（stage_content 渲染）- `src/swallowloop/interfaces/web/src/components/StageContent.vue`
- [ ] T030 [P] [US1] 阶段状态显示（待审批、执行中、已完成等）- `src/swallowloop/interfaces/web/src/components/StageStatus.vue`

---

## Phase 6: User Story 2 - 阶段状态追踪（Priority: P2）

**Goal**: Web 界面看到每个阶段的清晰状态（等待中、执行中、已完成、已审批），便于了解进度

**Independent Test**: 通过 Web 界面查看 Issue 详情并验证状态显示

### 状态追踪功能

- [ ] T031 [P] [US2] 完善 Pipeline 状态 API，返回完整的 stages_status 列表 - `src/swallowloop/interfaces/web/api/deerflow.py`
- [ ] T032 [P] [US2] 阶段详情 Tab 显示所有历史阶段的状态时间线 - `src/swallowloop/interfaces/web/src/components/StageTimeline.vue`
- [ ] T033 [P] [US2] DeerFlow 执行状态实时显示（running/pending_approval 等）- `src/swallowloop/interfaces/web/src/components/PipelineStatus.vue`

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | 依赖 | 说明 |
|-------|------|------|
| Phase 1 (基础设施) | 无 | 可立即开始 |
| Phase 2 (测试) | Phase 1 | 测试优先 |
| Phase 3 (Pipeline 核心) | Phase 2 | TDD 驱动 |
| Phase 4 (US1 阶段) | Phase 3 | 8 个 Stage Task |
| Phase 5 (前端 UI) | Phase 3 | 可与 Phase 4 并行 |
| Phase 6 (US2) | Phase 3 | 可与 Phase 4,5 并行 |

### Within Each Phase

- Phase 1 任务可并行
- Phase 2 测试可并行
- Phase 4 的 8 个 Stage Task 可并行开发
- Phase 5、6 可与 Phase 4 并行

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1: 基础设施
2. 完成 Phase 2: 核心测试
3. 完成 Phase 3: Pipeline 核心（TDD 驱动）
4. 完成 Phase 4: SDD 阶段 Task
5. 完成 Phase 5: 前端审批 UI
6. **验证**: 完整流水线可运行

### Incremental Delivery

1. Phase 1 + 2 → 基础就绪 + 测试就绪
2. + Phase 3 → Pipeline 核心完成
3. + Phase 4 → SDD 9 阶段完成
4. + Phase 5 → 审批 UI 完成
5. + Phase 6 → 状态追踪完善

---

## Notes

- 所有任务使用中文描述
- P1 用户故事是 MVP，必须优先完成
- 遵循测试优先原则（Phase 2 在 Phase 3 之前）
- FR-006 审批日志由 T014 实现
