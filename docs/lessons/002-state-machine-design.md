# 状态机设计：审批驱动 vs 执行驱动

## 问题描述

新建 Issue 后，泳道图显示"待审批"状态，但用户期望 AI 先自动运行，运行完成后才需要人工审批。

## 问题分析

### 原状态机设计（审批驱动）

```
新建 Issue → PENDING（待审批）→ 人工审批 → AI 执行 → 下一阶段
```

**问题**：
- Issue 创建后立即需要人工介入审批
- AI 执行需要等待人工触发
- 不符合"AI 先工作，人类后审批"的预期

### 新状态机设计（执行驱动）

```
新建 Issue → AI 自动运行（RUNNING）→ 执行完成 → 待审批（PENDING）→ 人工审批 → 下一阶段
```

**优势**：
- AI 创建后立即开始工作，无需人工等待
- 人类看到 AI 执行结果后再审批
- 减少人工等待时间，提高效率

## 代码修改

### IssueService.create_issue

```python
def create_issue(self, title: str, description: str) -> Issue:
    """创建新 Issue（自动启动 AI 执行）"""
    issue = Issue(...)
    # 启动头脑风暴阶段（状态设为 RUNNING）
    issue.start_stage(Stage.BRAINSTORM)
    self._repo.save(issue)

    # 异步触发 AI 执行（不等待完成）
    self._executor.execute_stage_async(issue, Stage.BRAINSTORM)

    return issue
```

## 测试用例更新

测试用例需要同步更新以反映新行为：

```python
def test_approve_stage():
    issue = service.create_issue("测试 Issue", "测试描述")

    # 创建后自动启动 brainstorm，状态为 RUNNING
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

    # 审批通过后进入下一阶段
    updated = asyncio.run(service.approve_stage(issue_id, Stage.BRAINSTORM, "通过"))
    assert updated.get_stage_state(Stage.BRAINSTORM).status == StageStatus.APPROVED
    assert updated.current_stage == Stage.PLAN_FORMED
    assert updated.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.RUNNING
```

## 根因分析

**为什么测试没发现这个问题？**

1. 测试用例 `test_approve_stage` 假设创建时状态是 `PENDING`
2. 但用户实际期望：创建时 AI 自动运行，状态是 `RUNNING`
3. 测试只验证了技术实现，没有验证业务行为是否符合预期

**教训**：

- 单元测试不仅验证"代码能跑"，还要验证"行为正确"
- 对于状态机设计，应该在测试中体现业务场景
- 建议添加更多的端到端测试，验证完整的用户流程

## 相关文档

- `src/swallowloop/domain/model/stage.py` - Stage 和 StageStatus 定义
- `src/swallowloop/application/service/issue_service.py` - IssueService
- `tests/test_issue_service.py` - IssueService 测试
