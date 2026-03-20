import type { Issue, Stage, StageState } from './index';

// 创建空的阶段状态
function createEmptyStageState(issueId: string, stage: Stage): StageState {
  return {
    issueId,
    stage,
    status: 'pending',
    document: '',
    documentVersions: [],
    comments: [],
  };
}

// Mock Issue 1: 头脑风暴阶段，运行中
export const mockIssue1: Issue = {
  id: 'issue-1',
  title: '实现用户登录功能',
  description: '需要实现完整的用户登录注册流程',
  status: 'active',
  currentStage: 'brainstorm',
  createdAt: new Date('2026-03-18'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-1', 'brainstorm'),
      status: 'running',
      startedAt: new Date('2026-03-18T10:00:00'),
      document: `# 用户登录功能方案

## 方案一：传统 Session + Cookie 方案

### 优点
- 技术成熟稳定
- 适合 SSR 应用
- 服务端可控性强

### 缺点
- 需要 session 存储
- 扩展性受限

---

## 方案二：JWT Token 方案

### 优点
- 无状态，扩展性好
- 适合前后端分离
- 支持移动端

### 缺点
- token 过期处理复杂
- 无法主动注销`,
      comments: [
        {
          id: 'c1',
          stage: 'brainstorm',
          action: 'approve',
          content: '方案二更适合我们的系统架构',
          createdAt: new Date('2026-03-19'),
        },
      ],
    },
    planFormed: createEmptyStageState('issue-1', 'planFormed'),
    detailedDesign: createEmptyStageState('issue-1', 'detailedDesign'),
    taskSplit: createEmptyStageState('issue-1', 'taskSplit'),
    execution: createEmptyStageState('issue-1', 'execution'),
    updateDocs: createEmptyStageState('issue-1', 'updateDocs'),
    submit: createEmptyStageState('issue-1', 'submit'),
  },
};

// Mock Issue 2: 执行阶段，显示进度50%
export const mockIssue2: Issue = {
  id: 'issue-2',
  title: '添加 GitHub Actions CI/CD',
  description: '配置 GitHub Actions 实现自动化测试和部署',
  status: 'active',
  currentStage: 'execution',
  createdAt: new Date('2026-03-15'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-2', 'brainstorm'),
      status: 'approved',
      document: '# CI/CD 流水线方案\n\n采用 GitHub Actions 实现...',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T09:00:00'),
      completedAt: new Date('2026-03-15T09:30:00'),
    },
    planFormed: {
      ...createEmptyStageState('issue-2', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n1. 配置 workflow\n2. 添加测试步骤\n3. 配置部署...',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T09:30:00'),
      completedAt: new Date('2026-03-15T10:30:00'),
    },
    detailedDesign: {
      ...createEmptyStageState('issue-2', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\nYAML 配置详解...',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T10:30:00'),
      completedAt: new Date('2026-03-15T12:00:00'),
    },
    taskSplit: {
      ...createEmptyStageState('issue-2', 'taskSplit'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已创建',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T12:00:00'),
      completedAt: new Date('2026-03-15T12:30:00'),
    },
    execution: {
      ...createEmptyStageState('issue-2', 'execution'),
      status: 'running',
      document: '# 执行中\n\n正在配置 GitHub Actions...',
      todoList: [
        { id: 't1', content: '创建 workflow 文件', status: 'completed' },
        { id: 't2', content: '配置测试 job', status: 'completed' },
        { id: 't3', content: '配置部署 job', status: 'in_progress' },
        { id: 't4', content: '添加通知机制', status: 'pending' },
        { id: 't5', content: '测试完整流程', status: 'pending' },
      ],
      progress: 50,
      executionState: 'running',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T12:30:00'),
    },
    updateDocs: createEmptyStageState('issue-2', 'updateDocs'),
    submit: createEmptyStageState('issue-2', 'submit'),
  },
};

// Mock Issue 3: 详细设计阶段，已打回
export const mockIssue3: Issue = {
  id: 'issue-3',
  title: '优化数据库查询性能',
  description: '分析并优化慢查询，提升系统性能',
  status: 'active',
  currentStage: 'detailedDesign',
  createdAt: new Date('2026-03-10'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-3', 'brainstorm'),
      status: 'approved',
      document: '# 性能优化方案\n\n决定采用索引优化方案...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-3', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n分阶段进行优化...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-3', 'detailedDesign'),
      status: 'rejected',
      document: '# 详细设计\n\n索引设计：\n1. idx_user_id\n2. idx_created_at',
      comments: [
        {
          id: 'c2',
          stage: 'detailedDesign',
          action: 'reject',
          content: '缺少对现有索引的分析，需要先执行 EXPLAIN 分析现有慢查询',
          createdAt: new Date('2026-03-17'),
        },
      ],
      documentVersions: [],
    },
    taskSplit: createEmptyStageState('issue-3', 'taskSplit'),
    execution: createEmptyStageState('issue-3', 'execution'),
    updateDocs: createEmptyStageState('issue-3', 'updateDocs'),
    submit: createEmptyStageState('issue-3', 'submit'),
  },
};

// Mock Issue 4: 已归档的 Issue
export const mockIssue4: Issue = {
  id: 'issue-4',
  title: '更新 README 文档',
  description: '更新项目 README 添加新功能说明',
  status: 'archived',
  currentStage: 'submit',
  createdAt: new Date('2026-03-01'),
  archivedAt: new Date('2026-03-16'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-4', 'brainstorm'),
      status: 'approved',
      document: '# 文档更新计划',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T10:00:00'),
      completedAt: new Date('2026-03-01T10:30:00'),
    },
    planFormed: {
      ...createEmptyStageState('issue-4', 'planFormed'),
      status: 'approved',
      document: '# 更新计划',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T10:30:00'),
      completedAt: new Date('2026-03-01T11:00:00'),
    },
    detailedDesign: {
      ...createEmptyStageState('issue-4', 'detailedDesign'),
      status: 'approved',
      document: '# 设计',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T11:00:00'),
      completedAt: new Date('2026-03-01T12:00:00'),
    },
    taskSplit: {
      ...createEmptyStageState('issue-4', 'taskSplit'),
      status: 'approved',
      document: '# 任务',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T12:00:00'),
      completedAt: new Date('2026-03-01T12:30:00'),
    },
    execution: {
      ...createEmptyStageState('issue-4', 'execution'),
      status: 'approved',
      document: '# 执行',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T12:30:00'),
      completedAt: new Date('2026-03-01T14:00:00'),
    },
    updateDocs: {
      ...createEmptyStageState('issue-4', 'updateDocs'),
      status: 'approved',
      document: '# 文档更新',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T14:00:00'),
      completedAt: new Date('2026-03-01T15:00:00'),
    },
    submit: {
      ...createEmptyStageState('issue-4', 'submit'),
      status: 'approved',
      document: '# 提交\n\nPR 已合并',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T15:00:00'),
      completedAt: new Date('2026-03-01T16:00:00'),
    },
  },
};

// Mock Issue 5: 头脑风暴阶段 - error
export const mockIssue5: Issue = {
  id: 'issue-5',
  title: '实现邮件通知功能',
  description: '添加邮件通知功能，通知用户任务状态变更',
  status: 'active',
  currentStage: 'brainstorm',
  createdAt: new Date('2026-03-19'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-5', 'brainstorm'),
      status: 'error',
      document: '# 邮件通知方案\n\n采用 SendGrid API...',
      comments: [
        {
          id: 'c5',
          stage: 'brainstorm',
          action: 'reject',
          content: 'SendGrid API 成本过高，考虑使用免费方案',
          createdAt: new Date('2026-03-19'),
        },
      ],
      documentVersions: [],
    },
    planFormed: createEmptyStageState('issue-5', 'planFormed'),
    detailedDesign: createEmptyStageState('issue-5', 'detailedDesign'),
    taskSplit: createEmptyStageState('issue-5', 'taskSplit'),
    execution: createEmptyStageState('issue-5', 'execution'),
    updateDocs: createEmptyStageState('issue-5', 'updateDocs'),
    submit: createEmptyStageState('issue-5', 'submit'),
  },
};

// Mock Issue 6: 方案成型阶段 - running
export const mockIssue6: Issue = {
  id: 'issue-6',
  title: '添加 WebSocket 实时通信',
  description: '实现实时任务状态推送功能',
  status: 'active',
  currentStage: 'planFormed',
  createdAt: new Date('2026-03-17'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-6', 'brainstorm'),
      status: 'approved',
      document: '# WebSocket 方案\n\n采用 Socket.io...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-6', 'planFormed'),
      status: 'running',
      document: '# 整体实现思路\n\n1. 建立连接\n2. 心跳检测\n3. 消息推送...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: createEmptyStageState('issue-6', 'detailedDesign'),
    taskSplit: createEmptyStageState('issue-6', 'taskSplit'),
    execution: createEmptyStageState('issue-6', 'execution'),
    updateDocs: createEmptyStageState('issue-6', 'updateDocs'),
    submit: createEmptyStageState('issue-6', 'submit'),
  },
};

// Mock Issue 7: 详细设计阶段 - approved
export const mockIssue7: Issue = {
  id: 'issue-7',
  title: '用户权限管理系统',
  description: '实现基于 RBAC 的权限控制',
  status: 'active',
  currentStage: 'detailedDesign',
  createdAt: new Date('2026-03-12'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-7', 'brainstorm'),
      status: 'approved',
      document: '# 权限管理方案\n\n采用 RBAC 模型...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-7', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n采用 RBAC 模型...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-7', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\n角色定义...\n权限表设计...',
      comments: [],
      documentVersions: [],
    },
    taskSplit: createEmptyStageState('issue-7', 'taskSplit'),
    execution: createEmptyStageState('issue-7', 'execution'),
    updateDocs: createEmptyStageState('issue-7', 'updateDocs'),
    submit: createEmptyStageState('issue-7', 'submit'),
  },
};

// Mock Issue 8: 任务拆分阶段 - pending
export const mockIssue8: Issue = {
  id: 'issue-8',
  title: '移动端适配优化',
  description: '优化移动端用户体验',
  status: 'active',
  currentStage: 'taskSplit',
  createdAt: new Date('2026-03-14'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-8', 'brainstorm'),
      status: 'approved',
      document: '# 移动端适配方案\n\n采用响应式设计...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-8', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n1. 响应式布局\n2. 触摸优化...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-8', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\n断点设计...\n组件适配...',
      comments: [],
      documentVersions: [],
    },
    taskSplit: {
      ...createEmptyStageState('issue-8', 'taskSplit'),
      status: 'pending',
      document: '# 任务拆分\n\nTODO 列表创建中...',
      comments: [],
      documentVersions: [],
    },
    execution: createEmptyStageState('issue-8', 'execution'),
    updateDocs: createEmptyStageState('issue-8', 'updateDocs'),
    submit: createEmptyStageState('issue-8', 'submit'),
  },
};

// Mock Issue 9: 执行阶段 - 75%
export const mockIssue9: Issue = {
  id: 'issue-9',
  title: '日志收集系统重构',
  description: '重构日志收集系统，支持分布式日志',
  status: 'active',
  currentStage: 'execution',
  createdAt: new Date('2026-03-08'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-9', 'brainstorm'),
      status: 'approved',
      document: '# 日志重构方案\n\n采用 ELK 技术栈...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-9', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n1. 搭建 ELK\n2. 迁移数据...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-9', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\nElasticsearch 配置...',
      comments: [],
      documentVersions: [],
    },
    taskSplit: {
      ...createEmptyStageState('issue-9', 'taskSplit'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已完成',
      comments: [],
      documentVersions: [],
    },
    execution: {
      ...createEmptyStageState('issue-9', 'execution'),
      status: 'pending',
      document: '# 执行中\n\n正在部署 Elasticsearch...',
      todoList: [
        { id: 't1', content: '搭建 Elasticsearch 集群', status: 'completed' },
        { id: 't2', content: '配置 Logstash', status: 'completed' },
        { id: 't3', content: '部署 Kibana', status: 'completed' },
        { id: 't4', content: '迁移历史日志', status: 'in_progress' },
        { id: 't5', content: '验证日志搜索', status: 'pending' },
      ],
      progress: 75,
      executionState: 'running',
      comments: [],
      documentVersions: [],
    },
    updateDocs: createEmptyStageState('issue-9', 'updateDocs'),
    submit: createEmptyStageState('issue-9', 'submit'),
  },
};

// Mock Issue 10: 更新文档阶段
export const mockIssue10: Issue = {
  id: 'issue-10',
  title: 'API 文档自动生成',
  description: '配置 API 文档自动生成工具',
  status: 'active',
  currentStage: 'updateDocs',
  createdAt: new Date('2026-03-05'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-10', 'brainstorm'),
      status: 'approved',
      document: '# API 文档方案\n\n采用 Swagger...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-10', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n1. 集成 Swagger\n2. 配置注解...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-10', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\nSwagger 配置...',
      comments: [],
      documentVersions: [],
    },
    taskSplit: {
      ...createEmptyStageState('issue-10', 'taskSplit'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已完成',
      comments: [],
      documentVersions: [],
    },
    execution: {
      ...createEmptyStageState('issue-10', 'execution'),
      status: 'approved',
      document: '# 执行完成\n\nAPI 文档已生成',
      comments: [],
      documentVersions: [],
    },
    updateDocs: {
      ...createEmptyStageState('issue-10', 'updateDocs'),
      status: 'pending',
      document: '# 文档更新\n\n正在更新 API 文档...',
      comments: [],
      documentVersions: [],
    },
    submit: createEmptyStageState('issue-10', 'submit'),
  },
};

// Mock Issue 11: 提交阶段
export const mockIssue11: Issue = {
  id: 'issue-11',
  title: '性能监控告警系统',
  description: '添加应用性能监控和告警功能',
  status: 'active',
  currentStage: 'submit',
  createdAt: new Date('2026-03-01'),
  stages: {
    brainstorm: {
      ...createEmptyStageState('issue-11', 'brainstorm'),
      status: 'approved',
      document: '# 监控方案\n\n采用 Prometheus...',
      comments: [],
      documentVersions: [],
    },
    planFormed: {
      ...createEmptyStageState('issue-11', 'planFormed'),
      status: 'approved',
      document: '# 实现计划\n\n1. 部署 Prometheus\n2. 配置告警规则...',
      comments: [],
      documentVersions: [],
    },
    detailedDesign: {
      ...createEmptyStageState('issue-11', 'detailedDesign'),
      status: 'approved',
      document: '# 详细设计\n\n监控指标定义...',
      comments: [],
      documentVersions: [],
    },
    taskSplit: {
      ...createEmptyStageState('issue-11', 'taskSplit'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已完成',
      comments: [],
      documentVersions: [],
    },
    execution: {
      ...createEmptyStageState('issue-11', 'execution'),
      status: 'approved',
      document: '# 执行完成\n\n监控系统已部署',
      comments: [],
      documentVersions: [],
    },
    updateDocs: {
      ...createEmptyStageState('issue-11', 'updateDocs'),
      status: 'approved',
      document: '# 文档更新\n\n已更新监控文档',
      comments: [],
      documentVersions: [],
    },
    submit: {
      ...createEmptyStageState('issue-11', 'submit'),
      status: 'pending',
      document: '# 待提交\n\n等待最终审核...',
      comments: [],
      documentVersions: [],
    },
  },
};

// Mock 执行日志
export const mockExecutionLogs = [
  { id: 'l1', timestamp: new Date('2026-03-19T10:00:00'), level: 'info' as const, message: '开始执行任务' },
  { id: 'l2', timestamp: new Date('2026-03-19T10:00:01'), level: 'success' as const, message: '创建 workflow 文件成功' },
  { id: 'l3', timestamp: new Date('2026-03-19T10:00:02'), level: 'info' as const, message: '配置测试 job' },
  { id: 'l4', timestamp: new Date('2026-03-19T10:00:03'), level: 'success' as const, message: '测试 job 配置完成' },
  { id: 'l5', timestamp: new Date('2026-03-19T10:00:04'), level: 'info' as const, message: '配置部署 job' },
  { id: 'l6', timestamp: new Date('2026-03-19T10:00:05'), level: 'warn' as const, message: '检测到缺少 DEPLOY_KEY' },
  { id: 'l7', timestamp: new Date('2026-03-19T10:00:06'), level: 'error' as const, message: '部署 job 配置失败' },
];

// 所有 Mock Issues
export const mockIssues: Issue[] = [
  mockIssue1, mockIssue2, mockIssue3, mockIssue4,
  mockIssue5, mockIssue6, mockIssue7, mockIssue8,
  mockIssue9, mockIssue10, mockIssue11
];
