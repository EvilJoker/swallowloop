# SwallowLoop 测试场景设计

## 概述

本文档定义 SwallowLoop 系统的功能测试场景，覆盖核心功能、边界条件和异常处理。

---

## 1. 基础场景

### 1.1 新任务处理

**场景描述**: 用户创建带 `swallow` 标签的 Issue，系统自动处理并创建 PR。

**前置条件**:
- SwallowLoop 服务运行中
- 目标仓库存在且可访问

**测试步骤**:
1. 在目标仓库创建 Issue，标题为「添加 hello 函数」，添加 `swallow` 标签
2. 等待一个轮询周期（默认 60 秒）
3. 观察任务状态变化

**预期结果**:
- 任务状态流转: `new → assigned → pending → in_progress → submitted`
- 创建新分支: `feature_{issue_number}_{date}-{slug}`
- 生成符合 Conventional Commits 格式的 commit message
- 自动创建 PR，标题与 commit message 一致
- Dashboard 显示任务执行日志

**验证方法**:
```bash
# 查看任务状态
cat ~/.swallowloop/tasks.json | jq .

# 查看 PR 列表
gh pr list --repo $GITHUB_REPO
```

---

### 1.2 Issue 关闭导致任务中止

**场景描述**: 任务执行过程中，用户关闭 Issue，系统中止任务。

**前置条件**:
- 任务状态为 `in_progress`

**测试步骤**:
1. 关闭正在执行的 Issue
2. 等待下一个轮询周期

**预期结果**:
- 任务状态变为 `aborted`
- Worker 进程被终止
- 工作空间被清理

---

### 1.3 PR 创建成功

**场景描述**: 任务执行完成后，系统自动创建 PR。

**验证点**:
- PR 标题格式: `{type}: {description}`
- PR body 包含 `Closes #{issue_number}`
- PR 指向正确的 base 分支

---

## 2. 并发场景

### 2.1 多任务并行执行

**场景描述**: 同时创建多个 Issue，验证并发执行。

**前置条件**:
- `MAX_WORKERS=3`（或更高）

**测试步骤**:
1. 同时创建 3 个带 `swallow` 标签的 Issue
2. 观察执行过程

**预期结果**:
- 3 个 Worker 同时启动
- 日志显示「当前活跃 Worker: 3」
- 3 个任务并行执行
- 各自创建独立的分支和 PR

**验证方法**:
```bash
# 查看 Worker 进程
ps aux | grep swallowloop

# 查看 Dashboard 状态
curl http://localhost:8080/api/stats
```

---

### 2.2 达到最大 Worker 限制

**场景描述**: 任务数量超过 `MAX_WORKERS` 配置。

**前置条件**:
- `MAX_WORKERS=2`

**测试步骤**:
1. 同时创建 5 个带 `swallow` 标签的 Issue
2. 观察执行过程

**预期结果**:
- 前 2 个任务立即执行
- 日志显示「并发限制：本次启动 2 个任务，3 个任务排队等待」
- 任务完成后，排队任务依次执行

---

### 2.3 Worker 超时处理

**场景描述**: Worker 执行时间超过 2 小时。

**测试步骤**:
1. 创建一个需要长时间处理的 Issue（或模拟超时）
2. 等待 2 小时

**预期结果**:
- Worker 进程被终止
- 任务状态标记为失败
- 生成错误消息「Worker 超时」
- 进入重试流程

---

## 3. 重试场景

### 3.1 任务执行失败自动重试

**场景描述**: Agent 执行失败，系统自动重试。

**前置条件**:
- 模拟 Agent 执行失败（如网络异常、API 错误）

**测试步骤**:
1. 创建 Issue 触发任务执行
2. 模拟执行失败
3. 观察任务状态

**预期结果**:
- 任务状态从 `in_progress` 变为 `pending`
- `retry_count` 增加 1
- 下一个轮询周期重新执行
- 日志显示「任务准备重试」

---

### 3.2 达到最大重试次数

**场景描述**: 任务重试 5 次后仍失败。

**前置条件**:
- `retry_count = 4`（已重试 4 次）

**测试步骤**:
1. 第 5 次执行失败
2. 观察任务状态

**预期结果**:
- 任务状态变为 `aborted`
- 在 Issue 上评论通知失败原因
- 不再重试

---

## 4. 修改场景

### 4.1 用户评论触发修改

**场景描述**: PR 创建后，用户在 Issue 上评论反馈，系统修改代码。

**前置条件**:
- 任务状态为 `submitted`
- PR 已创建

**测试步骤**:
1. 在 Issue 上评论「请把函数名改成 say_hello」
2. 等待下一个轮询周期

**预期结果**:
- 任务状态流转: `submitted → pending → in_progress`
- 在现有分支上修改代码
- 使用 `git commit --amend` 更新 commit
- 强制推送更新 PR
- PR 内容更新

---

### 4.2 连续多次修改

**场景描述**: 用户多次评论反馈，系统多次修改。

**测试步骤**:
1. 第一次评论「修改函数名」
2. 等待修改完成
3. 第二次评论「添加文档注释」

**预期结果**:
- 每次修改都使用 `--amend`
- PR 保持单个 commit
- `submission_count` 增加

---

## 5. 边界场景

### 5.1 网络异常处理

**场景描述**: GitHub API 请求失败。

**测试步骤**:
1. 模拟网络中断或 GitHub API 限流
2. 观察系统行为

**预期结果**:
- 日志记录错误信息
- 不影响其他任务执行
- 下一个轮询周期重试

---

### 5.2 Agent 不可用

**场景描述**: IFlow SDK 未安装或配置错误。

**测试步骤**:
1. 移除 `iflow-cli-sdk` 或配置错误的 API Key
2. 启动 SwallowLoop

**预期结果**:
- 启动时检测 Agent 不可用
- 输出错误信息
- 退出程序

---

### 5.3 JSON 文件并发写入

**场景描述**: 多个 Worker 同时更新任务状态。

**前置条件**:
- `MAX_WORKERS=5`
- 5 个任务同时执行

**预期结果**:
- 使用文件锁保护写入
- 数据不损坏
- 状态正确更新

---

### 5.4 空工作空间处理

**场景描述**: 任务执行完成后，工作空间不存在。

**测试步骤**:
1. 手动删除工作空间目录
2. 触发修改任务

**预期结果**:
- 重新克隆仓库
- 任务正常执行

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
- 执行 `exec` 替换当前进程
- 服务重启

---

### 6.2 禁用自更新

**场景描述**: `ENABLE_SELF_UPDATE=false` 时不检查更新。

**预期结果**:
- 不执行更新检查
- 服务持续运行

---

## 7. Web Dashboard 场景

### 7.1 任务列表查询

**测试步骤**:
```bash
curl http://localhost:8080/api/tasks
```

**预期结果**:
- 返回所有任务列表
- 包含状态、标题、PR 链接等信息
- 按更新时间倒序排列

---

### 7.2 任务详情查询

**测试步骤**:
```bash
curl http://localhost:8080/api/tasks/{issue_number}
```

**预期结果**:
- 返回任务详情
- 包含工作空间路径、重试次数、Worker PID 等

---

### 7.3 实时日志推送

**测试步骤**:
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/tasks/{issue_number}');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

**预期结果**:
- 连接成功
- 收到历史日志（最近 100 条）
- 收到实时日志推送

---

### 7.4 统计信息查询

**测试步骤**:
```bash
curl http://localhost:8080/api/stats
```

**预期结果**:
```json
{
  "total": 10,
  "active": 3,
  "completed": 5,
  "aborted": 1,
  "in_progress": 2,
  "pending": 1
}
```

---

## 8. AI Commit Message 场景

### 8.1 新功能提交

**场景**: 新增功能代码。

**预期 commit 格式**:
```
feat: 添加用户登录功能
```

---

### 8.2 Bug 修复提交

**场景**: 修复 bug 代码。

**预期 commit 格式**:
```
fix: 修复登录验证失败问题
```

---

### 8.3 文档更新提交

**场景**: 更新文档。

**预期 commit 格式**:
```
docs: 更新 README 配置说明
```

---

## 9. 测试执行清单

| 场景编号 | 场景名称 | 优先级 | 自动化 |
|---------|---------|-------|--------|
| 1.1 | 新任务处理 | P0 | 是 |
| 1.2 | Issue 关闭中止 | P0 | 是 |
| 2.1 | 多任务并行 | P0 | 是 |
| 2.2 | 最大 Worker 限制 | P1 | 是 |
| 3.1 | 自动重试 | P0 | 是 |
| 3.2 | 最大重试次数 | P1 | 是 |
| 4.1 | 评论触发修改 | P0 | 是 |
| 5.1 | 网络异常 | P1 | 手动 |
| 5.2 | Agent 不可用 | P1 | 手动 |
| 5.3 | 并发写入 | P1 | 是 |
| 6.1 | 自更新 | P2 | 手动 |
| 7.1-7.4 | Dashboard API | P1 | 是 |

---

## 10. 测试环境准备

### 环境变量

```bash
export GITHUB_TOKEN=your_token
export GITHUB_REPO=owner/repo
export MAX_WORKERS=3
export WEB_PORT=8080
export POLL_INTERVAL=30  # 测试时缩短轮询周期
```

### 测试数据准备

1. 创建测试仓库
2. 准备测试 Issue 模板
3. 配置测试标签 `swallow`

### 日志查看

```bash
# 查看服务日志
tail -f ~/.swallowloop/logs/swallowloop.log

# 查看任务数据
cat ~/.swallowloop/tasks.json | jq .

# 查看工作空间
ls -la ~/.swallowloop/workspaces/
```
