# SDD Stage Contract: 阶段执行与审批接口

**Branch**: `001-sdd-stage-migration` | **Date**: 2026-04-07

## 接口列表

### 1. 触发阶段执行

```
POST /api/issues/{issue_id}/trigger
```

**请求体**:
```json
{
  "stage": "specify"  // 阶段名称
}
```

**响应**:
```json
{
  "success": true,
  "message": "阶段已触发",
  "stage_status": {
    "state": "RUNNING",
    "reason": "正在执行..."
  }
}
```

### 2. 审批阶段

```
POST /api/issues/{issue_id}/approve
```

**请求体**:
```json
{
  "stage": "specify",
  "action": "approve",    // "approve" 或 "reject"
  "comments": "通过，很好"  // 打回时必填
}
```

**响应**:
```json
{
  "success": true,
  "message": "审批完成",
  "next_stage": "clarify"  // 下一个阶段名称
}
```

### 3. 查询 Issue 状态

```
GET /api/issues/{issue_id}
```

**响应**:
```json
{
  "id": "xxx",
  "title": "Issue 标题",
  "pipeline": {
    "current_stage": "specify",
    "state": "WAITING_APPROVAL",
    "stages": {
      "environment": { "state": "APPROVED", "stage_content": "..." },
      "specify": { "state": "WAITING_APPROVAL", "stage_content": "..." }
    }
  }
}
```

## 阶段状态枚举

| 状态 | 说明 | 触发条件 |
|------|------|---------|
| PENDING | 等待执行 | 上一阶段审批通过 |
| RUNNING | 执行中 | 调用 trigger |
| WAITING_APPROVAL | 等待审批 | 阶段执行完成 |
| APPROVED | 已通过 | 用户审批通过 |
| REJECTED | 已打回 | 用户审批打回 |
| FAILED | 执行失败 | 超时或 DeerFlow 错误 |

## 验证规则

1. 触发阶段时，当前阶段必须为 `APPROVED` 或 `PENDING`
2. 审批时，`action=reject` 必须包含 `comments`
3. 只有 `WAITING_APPROVAL` 状态的阶段可以审批
4. 审批通过后自动进入下一阶段（设置 state=PENDING）