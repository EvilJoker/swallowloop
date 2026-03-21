// 阶段类型
export type Stage =
  | 'brainstorm'
  | 'planFormed'
  | 'detailedDesign'
  | 'taskSplit'
  | 'execution'
  | 'updateDocs'
  | 'submit';

// 阶段状态
export type StageStatus = 'pending' | 'approved' | 'rejected' | 'running' | 'error';

// Issue 状态
export type IssueStatus = 'active' | 'archived' | 'discarded';

// 执行状态
export type ExecutionState = 'pending' | 'running' | 'paused' | 'success' | 'failed';

// TODO 项
export interface TodoItem {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

// 文档版本
export interface DocumentVersion {
  version: number;
  content: string;
  updatedAt: Date;
  updatedBy: 'ai' | 'user';
}

// 评论
export interface Comment {
  id: string;
  stage: Stage;
  action: 'approve' | 'reject';
  content: string;
  createdAt: Date;
}

// 阶段状态
export interface StageState {
  stage: Stage;
  status: StageStatus;
  document: string;
  documentVersions: DocumentVersion[];
  comments: Comment[];
  todoList?: TodoItem[];
  progress?: number;
  executionState?: ExecutionState;
  startedAt?: Date;     // 阶段开始时间
  completedAt?: Date;    // 阶段完成时间
}

// Issue
export interface Issue {
  id: string;
  title: string;
  description: string;
  status: IssueStatus;
  currentStage: Stage;
  createdAt: Date;
  archivedAt?: Date;
  discardedAt?: Date;
  deleteAt?: Date;
  stages: Record<Stage, StageState>;
}

// 阶段显示配置
export const STAGES: { key: Stage; label: string }[] = [
  { key: 'brainstorm', label: '头脑风暴' },
  { key: 'planFormed', label: '方案成型' },
  { key: 'detailedDesign', label: '详细设计' },
  { key: 'taskSplit', label: '任务拆分' },
  { key: 'execution', label: '执行' },
  { key: 'updateDocs', label: '更新文档' },
  { key: 'submit', label: '提交' },
];

// 状态颜色配置
export const STATUS_COLORS: Record<StageStatus, { bg: string; text: string; dot: string }> = {
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', dot: 'bg-yellow-500' },
  approved: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
  rejected: { bg: 'bg-purple-100', text: 'text-purple-800', dot: 'bg-purple-500' },
  running: { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-500' },
  error: { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-500' },
};

// 状态标签
export const STATUS_LABELS: Record<StageStatus, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已打回',
  running: '运行中',
  error: '异常',
};
