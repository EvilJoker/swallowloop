# SwallowLoop 测试场景设计

## 概述

本文档定义 SwallowLoop Issue 流水线系统的功能测试场景，覆盖核心功能、边界条件和异常处理。

---

## 1. Issue 生命周期场景

### 1.1 新建 Issue

**场景描述**: 用户创建一个新 Issue，系统自动进入头脑风暴阶段。

**测试步骤**:
1. POST `/api/issues` 创建 Issue
2. 观察返回的 Issue 状态

**预期结果**:
- Issue 状态为 `active`
- currentStage 为 `brainstorm`
- 所有 7 个阶段状态初始化为 `pending`

**验证方法**:
```bash
curl -X POST http://localhost:8080/api/issues \
  -H "Content-Type: application/json" \
  -d '{"title": "实现登录功能", "description": "需要实现用户登录"}'
```

---

### 1.2 归档 Issue

**场景描述**: Issue 流水线完成后，用户归档 Issue。

**测试步骤**:
1. PATCH `/api/issues/{id}` 设置 status 为 `archived`

**预期结果**:
- Issue 状态变为 `archived`
- `archivedAt` 时间戳被记录

---

### 1.3 废弃 Issue

**场景描述**: 用户永久废弃一个 Issue。

**测试步骤**:
1. PATCH `/api/issues/{id}` 设置 status 为 `discarded`

**预期结果**:
- Issue 状态变为 `discarded`
- `discardedAt` 时间戳被记录
- `deleteAt` 设置为废弃后 3 天

---

## 2. 流水线阶段场景

### 2.1 阶段审批通过

**场景描述**: 用户审批通过当前阶段。

**前置条件**:
- Issue 在 `brainstorm` 阶段，状态为 `pending`

**测试步骤**:
1. POST `/api/issues/{id}/stages/brainstorm/approve`
2. 观察阶段状态变化

**预期结果**:
- brainstorm 阶段状态变为 `approved`
- `completedAt` 被记录
- currentStage 自动进入 `planFormed`
- planFormed 阶段状态变为 `running`

---

### 2.2 阶段打回

**场景描述**: 用户打回当前阶段并提供修改意见。

**前置条件**:
- Issue 在 `planFormed` 阶段

**测试步骤**:
1. POST `/api/issues/{id}/stages/planFormed/reject`
   - body: `{"reason": "方案不够详细，需要增加错误处理"}`
2. 观察阶段状态

**预期结果**:
- planFormed 阶段状态变为 `rejected`
- 添加一条 `reject` 类型的 comment

---

### 2.3 重新触发 AI

**场景描述**: 阶段打回后，用户手动触发 AI 重新执行。

**前置条件**:
- Issue 在 `detailedDesign` 阶段，状态为 `rejected`

**测试步骤**:
1. POST `/api/issues/{id}/trigger`
   - body: `{"stage": "detailedDesign"}`

**预期结果**:
- 阶段状态变为 `running`
- 执行服务被调用

---

## 3. 执行阶段特殊场景

### 3.1 TODO 列表进度

**场景描述**: 执行阶段的 TODO 列表正确跟踪进度。

**前置条件**:
- Issue 在 `execution` 阶段

**预期结果**:
- `todoList` 包含多个 TODO 项
- `progress` 反映完成百分比
- `executionState` 反映执行状态

---

### 3.2 执行状态流转

**场景描述**: 执行阶段的子状态正确流转。

**前置条件**:
- Issue 在 `execution` 阶段

**预期状态流转**:
```
pending → running → success
                → failed
                → paused
```

---

## 4. WebSocket 场景

### 4.1 执行日志推送

**场景描述**: WebSocket 连接接收执行日志。

**测试步骤**:
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/execution/{issue_id}');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

**预期结果**:
- 连接成功
- 收到实时日志推送

---

## 5. 并发场景

### 5.1 JSON 文件并发写入

**场景描述**: 多个请求同时更新 Issue。

**前置条件**:
- 多个 API 请求同时修改不同 Issue

**预期结果**:
- 使用文件锁保护写入
- 数据不损坏
- 状态正确更新

---

## 6. 自更新场景

### 6.1 检测到新版本

**场景描述**: 远程仓库有新提交，系统自动更新。

**前置条件**:
- `ENABLE_SELF_UPDATE=true`
- 远程有新提交

**测试步骤**:
1. 在远程仓库推送新提交
2. 等待自更新检查周期（默认 5 分钟）

**预期结果**:
- 日志显示「发现新版本，准备更新」
- 执行 `git pull`
- 服务重启

---

### 6.2 禁用自更新

**场景描述**: `ENABLE_SELF_UPDATE=false` 时不检查更新。

**预期结果**:
- 不执行更新检查
- 服务持续运行

---

## 7. Web API 场景

### 7.1 Issue 列表查询

**测试步骤**:
```bash
curl http://localhost:8080/api/issues
```

**预期结果**:
- 返回所有 Issue 列表
- 包含状态、标题、当前阶段等信息

---

### 7.2 Issue 详情查询

**测试步骤**:
```bash
curl http://localhost:8080/api/issues/{id}
```

**预期结果**:
- 返回 Issue 详情
- 包含所有阶段状态

---

### 7.3 Issue 删除

**测试步骤**:
```bash
curl -X DELETE http://localhost:8080/api/issues/{id}
```

**预期结果**:
- Issue 被永久删除

---

## 8. 测试执行清单

| 场景编号 | 场景名称 | 优先级 | 自动化 |
|---------|---------|-------|--------|
| 1.1 | 新建 Issue | P0 | 是 |
| 1.2 | 归档 Issue | P1 | 是 |
| 1.3 | 废弃 Issue | P1 | 是 |
| 2.1 | 阶段审批通过 | P0 | 是 |
| 2.2 | 阶段打回 | P0 | 是 |
| 2.3 | 重新触发 AI | P1 | 是 |
| 3.1 | TODO 列表进度 | P1 | 是 |
| 3.2 | 执行状态流转 | P1 | 是 |
| 4.1 | WebSocket 日志 | P1 | 是 |
| 5.1 | 并发写入 | P1 | 是 |
| 6.1 | 自更新 | P2 | 手动 |
| 7.1 | Issue 列表查询 | P0 | 是 |
| 7.2 | Issue 详情查询 | P0 | 是 |
| 7.3 | Issue 删除 | P1 | 是 |

---

## 9. 测试环境准备

### 环境变量

```bash
export ISSUE_PROJECT=test_project
export WEB_PORT=8080
```

### 测试数据准备

1. 使用 API 创建测试 Issue
2. 验证状态流转

### API 基础 URL

```
http://localhost:8080/api
```
