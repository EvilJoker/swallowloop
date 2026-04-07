import type { Issue, Stage, StageState } from './index';

// 创建空的阶段状态
function createEmptyStageState(stage: Stage): StageState {
  return {
    stage,
    status: 'pending',
    document: '',
    documentVersions: [],
    comments: [],
  };
}

// Mock Issue 1: 规范定义阶段，运行中
export const mockIssue1: Issue = {
  id: 'issue-1',
  title: '实现用户登录功能',
  description: '需要实现完整的用户登录注册流程',
  status: 'active',
  currentStage: 'specify',
  createdAt: new Date('2026-03-18'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'running',
      startedAt: new Date('2026-03-18T10:00:00'),
      document: `# 用户登录功能规范定义

## 需求范围
- 用户注册
- 用户登录
- 密码找回
- 记住登录状态

## 验收标准
1. 支持邮箱注册
2. 支持密码强度校验
3. 登录状态保持 7 天
4. 支持退出登录

## 约束条件
- 必须使用 HTTPS
- 密码必须加密存储
- 需要防暴力破解`,
      comments: [],
    },
    clarify: createEmptyStageState('clarify'),
    plan: createEmptyStageState('plan'),
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
  runningStatus: 'in_progress',
  pipeline: {
    name: 'Issue-issue-1',
    stages: [
      {
        name: 'environment',
        label: '环境准备',
        status: 'approved',
        tasks: [
          { name: '创建工作空间', status: 'success' },
          { name: 'Clone 代码库', status: 'success' },
          { name: '切换分支', status: 'success' },
        ],
      },
      {
        name: 'specify',
        label: '规范定义',
        status: 'running',
        tasks: [
          { name: '定义需求范围', status: 'success' },
          { name: '定义验收标准', status: 'running' },
          { name: '识别约束条件', status: 'pending' },
        ],
      },
      {
        name: 'clarify',
        label: '需求澄清',
        status: 'new',
        tasks: [],
      },
      {
        name: 'plan',
        label: '技术规划',
        status: 'new',
        tasks: [],
      },
      {
        name: 'checklist',
        label: '质量检查',
        status: 'new',
        tasks: [],
      },
      {
        name: 'tasks',
        label: '任务拆分',
        status: 'new',
        tasks: [],
      },
      {
        name: 'analyze',
        label: '一致性分析',
        status: 'new',
        tasks: [],
      },
      {
        name: 'implement',
        label: '编码实现',
        status: 'new',
        tasks: [],
      },
      {
        name: 'submit',
        label: '提交发布',
        status: 'new',
        tasks: [],
      },
    ],
    currentStageIndex: 1,
    isDone: false,
  },
};

// Mock Issue 2: 需求澄清阶段，显示进度50%
export const mockIssue2: Issue = {
  id: 'issue-2',
  title: '添加 GitHub Actions CI/CD',
  description: '配置 GitHub Actions 实现自动化测试和部署',
  status: 'active',
  currentStage: 'clarify',
  createdAt: new Date('2026-03-15'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# CI/CD 规范定义\n\n目标：实现自动化测试和部署...',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T09:00:00'),
      completedAt: new Date('2026-03-15T09:30:00'),
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'running',
      document: '# 需求澄清\n\n1. 测试覆盖率目标\n2. 部署环境确认...',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-15T09:30:00'),
    },
    plan: createEmptyStageState('plan'),
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 3: 技术规划阶段，已打回
export const mockIssue3: Issue = {
  id: 'issue-3',
  title: '优化数据库查询性能',
  description: '分析并优化慢查询，提升系统性能',
  status: 'active',
  currentStage: 'plan',
  createdAt: new Date('2026-03-10'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 性能优化规范定义\n\n目标：分析并优化慢查询...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认优化范围...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'rejected',
      document: '# 技术规划\n\n索引设计：\n1. idx_user_id\n2. idx_created_at',
      comments: [
        {
          id: 'c2',
          stage: 'plan',
          action: 'reject',
          content: '缺少对现有索引的分析，需要先执行 EXPLAIN 分析现有慢查询',
          createdAt: new Date('2026-03-17'),
        },
      ],
      documentVersions: [],
    },
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
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
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 文档更新规范定义',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T10:00:00'),
      completedAt: new Date('2026-03-01T10:30:00'),
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T10:30:00'),
      completedAt: new Date('2026-03-01T11:00:00'),
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T11:00:00'),
      completedAt: new Date('2026-03-01T12:00:00'),
    },
    checklist: {
      ...createEmptyStageState('checklist'),
      status: 'approved',
      document: '# 质量检查',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T12:00:00'),
      completedAt: new Date('2026-03-01T12:30:00'),
    },
    tasks: {
      ...createEmptyStageState('tasks'),
      status: 'approved',
      document: '# 任务拆分',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T12:30:00'),
      completedAt: new Date('2026-03-01T14:00:00'),
    },
    analyze: {
      ...createEmptyStageState('analyze'),
      status: 'approved',
      document: '# 一致性分析',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T14:00:00'),
      completedAt: new Date('2026-03-01T15:00:00'),
    },
    implement: {
      ...createEmptyStageState('implement'),
      status: 'approved',
      document: '# 编码实现',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T15:00:00'),
      completedAt: new Date('2026-03-01T16:00:00'),
    },
    submit: {
      ...createEmptyStageState('submit'),
      status: 'approved',
      document: '# 提交\n\nPR 已合并',
      comments: [],
      documentVersions: [],
      startedAt: new Date('2026-03-01T16:00:00'),
      completedAt: new Date('2026-03-01T17:00:00'),
    },
  },
};

// Mock Issue 5: 规范定义阶段 - error
export const mockIssue5: Issue = {
  id: 'issue-5',
  title: '实现邮件通知功能',
  description: '添加邮件通知功能，通知用户任务状态变更',
  status: 'active',
  currentStage: 'specify',
  createdAt: new Date('2026-03-19'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'error',
      document: '# 邮件通知规范定义\n\n采用 SendGrid API...',
      comments: [
        {
          id: 'c5',
          stage: 'specify',
          action: 'reject',
          content: 'SendGrid API 成本过高，考虑使用免费方案',
          createdAt: new Date('2026-03-19'),
        },
      ],
      documentVersions: [],
    },
    clarify: createEmptyStageState('clarify'),
    plan: createEmptyStageState('plan'),
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 6: 需求澄清阶段 - running
export const mockIssue6: Issue = {
  id: 'issue-6',
  title: '添加 WebSocket 实时通信',
  description: '实现实时任务状态推送功能',
  status: 'active',
  currentStage: 'clarify',
  createdAt: new Date('2026-03-17'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# WebSocket 规范定义\n\n采用 Socket.io...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'running',
      document: '# 需求澄清\n\n1. 连接管理\n2. 心跳检测\n3. 消息推送...',
      comments: [],
      documentVersions: [],
    },
    plan: createEmptyStageState('plan'),
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 7: 技术规划阶段 - approved
export const mockIssue7: Issue = {
  id: 'issue-7',
  title: '用户权限管理系统',
  description: '实现基于 RBAC 的权限控制',
  status: 'active',
  currentStage: 'plan',
  createdAt: new Date('2026-03-12'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 权限管理规范定义\n\n采用 RBAC 模型...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认角色和权限...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划\n\n角色定义...\n权限表设计...',
      comments: [],
      documentVersions: [],
    },
    checklist: createEmptyStageState('checklist'),
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 8: 任务拆分阶段 - pending
export const mockIssue8: Issue = {
  id: 'issue-8',
  title: '移动端适配优化',
  description: '优化移动端用户体验',
  status: 'active',
  currentStage: 'tasks',
  createdAt: new Date('2026-03-14'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 移动端适配规范定义\n\n采用响应式设计...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认适配范围...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划\n\n1. 响应式布局\n2. 触摸优化...',
      comments: [],
      documentVersions: [],
    },
    checklist: {
      ...createEmptyStageState('checklist'),
      status: 'approved',
      document: '# 质量检查\n\n检查清单完成',
      comments: [],
      documentVersions: [],
    },
    tasks: {
      ...createEmptyStageState('tasks'),
      status: 'pending',
      document: '# 任务拆分\n\nTODO 列表创建中...',
      comments: [],
      documentVersions: [],
    },
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 9: 编码实现阶段 - 75%
export const mockIssue9: Issue = {
  id: 'issue-9',
  title: '日志收集系统重构',
  description: '重构日志收集系统，支持分布式日志',
  status: 'active',
  currentStage: 'implement',
  createdAt: new Date('2026-03-08'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 日志重构规范定义\n\n采用 ELK 技术栈...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认日志格式...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划\n\n1. 搭建 ELK\n2. 迁移数据...',
      comments: [],
      documentVersions: [],
    },
    checklist: {
      ...createEmptyStageState('checklist'),
      status: 'approved',
      document: '# 质量检查\n\n代码规范检查通过',
      comments: [],
      documentVersions: [],
    },
    tasks: {
      ...createEmptyStageState('tasks'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已完成',
      comments: [],
      documentVersions: [],
    },
    analyze: {
      ...createEmptyStageState('analyze'),
      status: 'approved',
      document: '# 一致性分析\n\n方案与任务一致性验证通过',
      comments: [],
      documentVersions: [],
    },
    implement: {
      ...createEmptyStageState('implement'),
      status: 'pending',
      document: '# 编码实现\n\n正在部署 Elasticsearch...',
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
    submit: createEmptyStageState('submit'),
  },
};

// Mock Issue 10: 质量检查阶段
export const mockIssue10: Issue = {
  id: 'issue-10',
  title: 'API 文档自动生成',
  description: '配置 API 文档自动生成工具',
  status: 'active',
  currentStage: 'checklist',
  createdAt: new Date('2026-03-05'),
  stages: {
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# API 文档规范定义\n\n采用 Swagger...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认文档范围...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划\n\n1. 集成 Swagger\n2. 配置注解...',
      comments: [],
      documentVersions: [],
    },
    checklist: {
      ...createEmptyStageState('checklist'),
      status: 'pending',
      document: '# 质量检查\n\n正在检查代码规范...',
      comments: [],
      documentVersions: [],
    },
    tasks: createEmptyStageState('tasks'),
    analyze: createEmptyStageState('analyze'),
    implement: createEmptyStageState('implement'),
    submit: createEmptyStageState('submit'),
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
    environment: createEmptyStageState('environment'),
    specify: {
      ...createEmptyStageState('specify'),
      status: 'approved',
      document: '# 监控规范定义\n\n采用 Prometheus...',
      comments: [],
      documentVersions: [],
    },
    clarify: {
      ...createEmptyStageState('clarify'),
      status: 'approved',
      document: '# 需求澄清\n\n确认监控指标...',
      comments: [],
      documentVersions: [],
    },
    plan: {
      ...createEmptyStageState('plan'),
      status: 'approved',
      document: '# 技术规划\n\n1. 部署 Prometheus\n2. 配置告警规则...',
      comments: [],
      documentVersions: [],
    },
    checklist: {
      ...createEmptyStageState('checklist'),
      status: 'approved',
      document: '# 质量检查\n\n检查通过',
      comments: [],
      documentVersions: [],
    },
    tasks: {
      ...createEmptyStageState('tasks'),
      status: 'approved',
      document: '# 任务拆分\n\nTODO 列表已完成',
      comments: [],
      documentVersions: [],
    },
    analyze: {
      ...createEmptyStageState('analyze'),
      status: 'approved',
      document: '# 一致性分析\n\n一致性验证通过',
      comments: [],
      documentVersions: [],
    },
    implement: {
      ...createEmptyStageState('implement'),
      status: 'approved',
      document: '# 编码实现\n\n监控系统已部署',
      comments: [],
      documentVersions: [],
    },
    submit: {
      ...createEmptyStageState('submit'),
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
