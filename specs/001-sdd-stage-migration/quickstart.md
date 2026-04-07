# Quickstart: SDD 阶段流水线

**Branch**: `001-sdd-stage-migration` | **Date**: 2026-04-07

## 开发环境

```bash
# 启动完整环境
./run.sh

# 运行测试
pytest tests/ -v
```

## 测试 SDD 流水线

### 1. 创建 Issue

```bash
curl -X POST http://localhost:9501/api/issues \
  -H "Content-Type: application/json" \
  -d '{"title":"测试 Issue","description":"描述内容"}'
```

### 2. 触发环境准备

```bash
curl -X POST "http://localhost:9501/api/issues/{issue_id}/trigger" \
  -H "Content-Type: application/json" \
  -d '{"stage":"environment"}'
```

### 3. 审批通过，进入下一阶段

```bash
curl -X POST "http://localhost:9501/api/issues/{issue_id}/approve" \
  -H "Content-Type: application/json" \
  -d '{"stage":"environment","comments":"通过"}'
```

### 4. 触发 specify 阶段

```bash
curl -X POST "http://localhost:9501/api/issues/{issue_id}/trigger" \
  -H "Content-Type: application/json" \
  -d '{"stage":"specify"}'
```

## 流水线状态查询

```bash
curl http://localhost:9501/api/issues/{issue_id}
```

返回的 `pipeline` 字段包含所有阶段状态。

## 阶段列表

| 阶段 | 说明 | 审批要求 |
|------|------|---------|
| environment | 环境准备（创建 workspace、clone 代码） | 不需要 |
| specify | 规范定义（使用 /speckit-specify） | 需要 |
| clarify | 需求澄清（使用 /speckit-clarify） | 需要 |
| plan | 技术规划（使用 /speckit-plan） | 需要 |
| checklist | 质量检查（使用 /speckit-checklist） | 需要 |
| tasks | 任务拆分（使用 /speckit-tasks） | 需要 |
| analyze | 一致性分析 | 需要 |
| implement | 编码实现 | 需要 |
| submit | 提交发布 | 需要 |

## 常见问题

### Q: DeerFlow 执行超时？

A: 标记阶段为 `FAILED`，用户可在 UI 手动重试。

### Q: 用户打回阶段？

A: 自动重新执行一次，仍失败则停止。

### Q: 多个 Issue 并发？

A: DeerFlow 一次执行一个任务，其他 Issue 排队等待。