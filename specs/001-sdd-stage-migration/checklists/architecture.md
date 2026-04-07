# Architecture Checklist: SDD 阶段流水线重构

**Purpose**: Validate architecture and design decisions against constitution principles
**Created**: 2026-04-07
**Feature**: [spec.md](../spec.md), [data-model.md](../data-model.md)

## DDD Architecture Compliance

- [ ] Stage/Task 类是否位于 domain 层（无外层依赖）？ [Spec §IV]
- [ ] DeerFlowAgent 是否只依赖 BaseAgent 接口（ABC + @abstractmethod）？ [Spec §IV]
- [ ] Infrastructure 层是否只依赖 Domain 接口？ [Spec §IV]
- [ ] 是否没有跨层反向依赖？ [Spec §IV]

## 最小化接口原则

- [ ] IssuePipeline 是否只暴露必要方法（execute*, set_*, get_*）？ [Spec §V]
- [ ] Stage 类是否隐藏内部实现细节（使用 _ 前缀）？ [Spec §V]
- [ ] Task 类是否暴露最小接口（execute, set_agent）？ [Spec §V]
- [ ] 是否使用 __all__ 显式声明公开 API？ [Spec §V]

## 人类决策权原则

- [ ] 是否每个阶段都需要人类审批才能进入下一阶段？ [Spec §I]
- [ ] 阶段打回是否必须包含反馈意见？ [Spec §I]
- [ ] 重新执行失败后是否停止流水线？ [Spec §I]

## 流水线透明性原则

- [ ] 阶段执行结果是否存储为 JSON/Markdown？ [Spec §II]
- [ ] 阶段转换是否记录时间戳和操作历史？ [Spec §II]
- [ ] 审批记录是否包含审批人、时间和意见？ [Spec §II]

## 测试优先原则

- [ ] 是否为每个阶段 Task 规划了单元测试？ [Spec §III]
- [ ] 是否规划了集成测试验证 Pipeline 状态转换？ [Spec §III]
- [ ] 是否规划了 E2E 测试验证完整流程？ [Spec §III]

## Data Model Consistency

- [ ] StageState 枚举是否与状态转换图一致？ [data-model.md]
- [ ] ApprovalState 是否覆盖所有审批场景？ [data-model.md]
- [ ] PipelineContext 是否包含所有必要的上下文字段？ [data-model.md]
- [ ] 验证规则是否与接口契约一致？ [data-model.md §验证规则]

## API Contract Consistency

- [ ] trigger 接口是否与 execute_stage 行为一致？ [contracts/sdd-stage-contract.md]
- [ ] approve 接口是否包含 next_stage 返回？ [contracts/sdd-stage-contract.md]
- [ ] 查询接口是否返回完整的 stage_content？ [contracts/sdd-stage-contract.md]
- [ ] 验证规则是否在 API 层正确执行？ [contracts/sdd-stage-contract.md]

## Notes

- 本 checklist 用于验证架构设计和数据模型的质量
- 实现前应确保所有条目通过