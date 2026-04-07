import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { Issue, PipelineStageInfo, PipelineTaskInfo, StageStatus } from '@/types';
import { CheckCircle2, Circle, Clock, XCircle, Loader2, GitBranch, Folder, Hash, ListTodo, Check, RotateCcw } from 'lucide-react';
import { issueApi } from '@/lib/api';

interface PipelineDetailProps {
  issue: Issue;
  onApprove?: (issue: Issue) => void;
  onRetry?: (issue: Issue, comment?: string) => void;
  onRefresh?: () => void;
  className?: string;
}

// 阶段状态配置
const STAGE_STATUS_CONFIG: Record<StageStatus, { icon: typeof Circle; color: string; bgColor: string; label: string }> = {
  new: { icon: Circle, color: 'text-slate-500', bgColor: 'bg-slate-100 text-slate-600', label: '未开始' },
  running: { icon: Loader2, color: 'text-blue-600', bgColor: 'bg-blue-500 text-white', label: '运行中' },
  pending: { icon: Clock, color: 'text-amber-600', bgColor: 'bg-amber-400 text-white', label: '待审批' },
  approved: { icon: CheckCircle2, color: 'text-emerald-600', bgColor: 'bg-emerald-500 text-white', label: '完成' },
  rejected: { icon: XCircle, color: 'text-purple-600', bgColor: 'bg-purple-400 text-white', label: '失败' },
  error: { icon: XCircle, color: 'text-red-600', bgColor: 'bg-red-500 text-white', label: '失败' },
};

// 任务状态配置
const TASK_STATUS_CONFIG: Record<string, { icon: typeof Circle; color: string; bgColor: string; label: string }> = {
  pending: { icon: Circle, color: 'text-slate-400', bgColor: 'bg-slate-100', label: '未开始' },
  running: { icon: Loader2, color: 'text-blue-500', bgColor: 'bg-blue-100', label: '执行中' },
  in_progress: { icon: Loader2, color: 'text-blue-500', bgColor: 'bg-blue-100', label: '执行中' },
  success: { icon: CheckCircle2, color: 'text-emerald-500', bgColor: 'bg-emerald-100', label: '完成' },
  completed: { icon: CheckCircle2, color: 'text-emerald-500', bgColor: 'bg-emerald-100', label: '完成' },
  failed: { icon: XCircle, color: 'text-red-500', bgColor: 'bg-red-100', label: '异常' },
};

function getStageDotClass(status: StageStatus, isCurrent: boolean): string {
  if (isCurrent) return 'bg-blue-500 text-white ring-blue-100';
  if (status === 'new' || !status) return 'bg-slate-200 text-slate-400 ring-slate-100';
  return STAGE_STATUS_CONFIG[status]?.bgColor || 'bg-slate-200 text-slate-400 ring-slate-100';
}

function getCardClass(isCurrent: boolean): string {
  return isCurrent ? 'bg-blue-50 border border-blue-200' : 'bg-white border border-slate-200';
}

function getTitleClass(isCurrent: boolean): string {
  return isCurrent ? 'text-blue-800' : 'text-slate-800';
}

// 渲染任务列表
function TaskList({ tasks }: { tasks: PipelineTaskInfo[] }) {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-xs text-slate-400 italic mt-2 flex items-center gap-1">
        <ListTodo className="w-3 h-3" />
        暂无任务
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-1">
      <div className="text-xs text-slate-500 flex items-center gap-1 mb-1">
        <ListTodo className="w-3 h-3" />
        任务 ({tasks.length})
      </div>
      {tasks.map((task, idx) => {
        const taskConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.pending;
        const TaskIcon = taskConfig.icon;
        return (
          <div key={idx} className={cn('flex items-center gap-2 text-xs p-1.5 rounded', taskConfig.bgColor)}>
            <TaskIcon className={cn('w-3.5 h-3.5', taskConfig.color, task.status === 'running' && 'animate-spin')} />
            <span className={cn('flex-1', ['success', 'completed'].includes(task.status) ? 'text-slate-500 line-through' : 'text-slate-700')}>
              {task.name}
            </span>
            <span className={cn('text-xs px-1 py-0.5 rounded font-medium', taskConfig.color)}>
              {taskConfig.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function EnvironmentStageItem({ stage, isCurrent, workspace, onApprove, onRetry }: {
  stage: PipelineStageInfo;
  isCurrent: boolean;
  workspace?: { repo_url?: string; branch?: string; thread_id?: string; workspace_path?: string } | null;
  onApprove?: () => void;
  onRetry?: () => void;
}) {
  const config = STAGE_STATUS_CONFIG[stage.status as StageStatus] || STAGE_STATUS_CONFIG.new;
  const isPending = stage.status === 'pending';
  const isError = stage.status === 'error';

  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-white mb-2">
      <div className="flex items-center gap-2 mb-2">
        {isCurrent && (
          <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded">当前</span>
        )}
        <span className={cn('text-sm font-medium', getTitleClass(isCurrent))}>
          {stage.label}
        </span>
        {/* 状态标签和操作按钮 */}
        <div className="flex items-center gap-1.5 ml-auto">
          {(isPending || isError) && (
            <>
              {isPending && (
                <button
                  onClick={onApprove}
                  className="p-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                  title="通过"
                >
                  <Check className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                onClick={onRetry}
                className="p-1 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors"
                title="重试"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          <span className={cn('text-xs px-2 py-1 rounded-full font-medium', config.bgColor)}>
            {config.label}
          </span>
        </div>
      </div>
      {workspace && workspace.workspace_path && (
        <div className="space-y-1 text-xs mb-2">
          <div className="flex items-center gap-2">
            <Hash className="w-3 h-3 text-slate-400" />
            <span className="text-slate-500">会话ID</span>
            <span className="text-slate-700 font-mono">{workspace.thread_id || '未设置'}</span>
          </div>
          <div className="flex items-center gap-2">
            <GitBranch className="w-3 h-3 text-slate-400" />
            <span className="text-slate-500">分支</span>
            <span className="text-slate-700">{workspace.branch || '未设置'}</span>
          </div>
          <div className="flex items-center gap-2">
            <Folder className="w-3 h-3 text-slate-400" />
            <span className="text-slate-500">目录</span>
            <span className="text-slate-700 font-mono truncate">{workspace.workspace_path || '未设置'}</span>
          </div>
        </div>
      )}
      {/* 任务列表 */}
      <TaskList tasks={stage.tasks} />
    </div>
  );
}

export function PipelineDetail({ issue, onApprove, onRetry, onRefresh, className }: PipelineDetailProps) {
  const pipeline = issue.pipeline;
  const [showRetryDialog, setShowRetryDialog] = useState(false);
  const [retryComment, setRetryComment] = useState('');
  const [isRetrying, setIsRetrying] = useState(false);

  if (!pipeline) {
    return (
      <div className={cn('flex items-center justify-center h-48 text-slate-400', className)}>
        暂无 Pipeline 信息
      </div>
    );
  }

  const handleApprove = async () => {
    try {
      await issueApi.approveStage(issue.id, 'environment', '审批通过');
      onApprove?.(issue);
      onRefresh?.();
    } catch (err) {
      console.error('审批失败:', err);
    }
  };

  const handleRetryWithComment = async () => {
    if (!retryComment.trim()) return;
    setIsRetrying(true);
    setShowRetryDialog(false);
    try {
      await issueApi.approveStage(issue.id, 'environment', retryComment);
      await issueApi.trigger(issue.id, 'environment');
      setRetryComment('');
      onRetry?.(issue, retryComment);
      onRefresh?.();
    } catch (err) {
      console.error('重试环境准备失败:', err);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className={cn('p-4', className)}>
      {/* Pipeline Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-slate-800">阶段详情</h3>
        <span className={cn(
          'text-xs px-2 py-1 rounded-full',
          pipeline.isDone ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'
        )}>
          {pipeline.isDone ? '已完成' : '进行中'}
        </span>
      </div>

      {/* 阶段列表 */}
      <div className="space-y-0">
        {pipeline.stages.map((stage, index) => {
          const isCurrent = index === pipeline.currentStageIndex;
          if (stage.name === 'environment') {
            return (
              <div key={stage.name} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center ring-4',
                    getStageDotClass(stage.status as StageStatus, isCurrent)
                  )}>
                    {(() => {
                      const Icon = STAGE_STATUS_CONFIG[stage.status as StageStatus]?.icon || Circle;
                      return <Icon className={cn('w-4 h-4', stage.status === 'running' && 'animate-spin')} />;
                    })()}
                  </div>
                  {index < pipeline.stages.length - 1 && (
                    <div className={cn('w-0.5 flex-1 mt-1', isCurrent ? 'bg-blue-300' : 'bg-slate-200')} />
                  )}
                </div>
                <div className="flex-1">
                  <EnvironmentStageItem
                    stage={stage}
                    isCurrent={isCurrent}
                    workspace={issue.workspace}
                    onApprove={handleApprove}
                    onRetry={() => setShowRetryDialog(true)}
                  />
                </div>
              </div>
            );
          }
          return (
            <div key={stage.name} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center ring-4',
                  getStageDotClass(stage.status as StageStatus, isCurrent)
                )}>
                  {(() => {
                    const Icon = STAGE_STATUS_CONFIG[stage.status as StageStatus]?.icon || Circle;
                    return <Icon className={cn('w-4 h-4', stage.status === 'running' && 'animate-spin')} />;
                  })()}
                </div>
                {index < pipeline.stages.length - 1 && (
                  <div className={cn('w-0.5 flex-1 mt-1', isCurrent ? 'bg-blue-300' : 'bg-slate-200')} />
                )}
              </div>
              <div className="flex-1">
                <div className={cn('rounded-lg p-3 mb-2', getCardClass(isCurrent))}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isCurrent && (
                        <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded">当前</span>
                      )}
                      <span className={cn('text-sm font-medium', getTitleClass(isCurrent))}>
                        {stage.label}
                      </span>
                    </div>
                    <span className={cn(
                      'text-xs px-2 py-1 rounded-full font-medium',
                      STAGE_STATUS_CONFIG[stage.status as StageStatus]?.bgColor || 'bg-slate-100'
                    )}>
                      {STAGE_STATUS_CONFIG[stage.status as StageStatus]?.label || '未开始'}
                    </span>
                  </div>
                  {/* 任务列表 */}
                  <TaskList tasks={stage.tasks} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 重试弹窗 */}
      {showRetryDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-4 w-80 shadow-xl">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              请输入改进意见（将传递给 AI 作为上下文）
            </label>
            <textarea
              value={retryComment}
              onChange={(e) => setRetryComment(e.target.value)}
              placeholder="例如：需要更好的错误处理、添加更多日志..."
              className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-slate-800 placeholder:text-slate-400"
              rows={3}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => {
                  setShowRetryDialog(false);
                  setRetryComment('');
                }}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors font-medium"
              >
                取消
              </button>
              <button
                onClick={handleRetryWithComment}
                disabled={!retryComment.trim() || isRetrying}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg transition-colors font-medium',
                  retryComment.trim() && !isRetrying
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                )}
              >
                {isRetrying ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    重试中...
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-4 h-4" />
                    确认重试
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
