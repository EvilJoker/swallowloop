import { Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Issue, IssueRunningStatus, StageStatus } from '@/types';
import { STAGES, STATUS_LABELS } from '@/types';

interface IssueCardProps {
  issue: Issue;
  onClick?: () => void;
  onDelete?: (issue: Issue) => void;
  draggable?: boolean;
  className?: string;
}

// 泳道边框颜色
const LANE_BORDER_CONFIG: Record<IssueRunningStatus, string> = {
  new: 'border-l-gray-400',
  in_progress: 'border-l-blue-400',
  done: 'border-l-emerald-400',
};

// 状态颜色配置
const STATUS_COLOR_CONFIG: Record<StageStatus, { bg: string; text: string }> = {
  new: { bg: 'bg-gray-100', text: 'text-gray-600' },
  running: { bg: 'bg-blue-100', text: 'text-blue-600' },
  pending: { bg: 'bg-amber-100', text: 'text-amber-600' },
  approved: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  rejected: { bg: 'bg-purple-100', text: 'text-purple-600' },
  error: { bg: 'bg-red-100', text: 'text-red-600' },
  completed: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  failed: { bg: 'bg-red-100', text: 'text-red-600' },
};

export function IssueCard({ issue, onClick, onDelete, draggable, className }: IssueCardProps) {
  const issueNumber = issue.id.replace('issue-', '');
  const currentStage = STAGES.find(s => s.key === issue.currentStage);
  const currentStageState = issue.stages[issue.currentStage];
  const stageStatus = currentStageState?.status || 'new';
  const statusColor = STATUS_COLOR_CONFIG[stageStatus as StageStatus] || STATUS_COLOR_CONFIG.new;

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('issueId', issue.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className={cn('relative group', className)}>
      <div
        role="button"
        tabIndex={0}
        draggable={draggable}
        onClick={onClick}
        onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
        onDragStart={handleDragStart}
        className={cn(
          'w-full p-3 bg-white rounded-xl border border-slate-200 border-l-4 shadow-sm text-left',
          'hover:shadow-md hover:border-slate-300 hover:-translate-y-0.5 transition-all',
          draggable ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
          LANE_BORDER_CONFIG[issue.runningStatus || 'new']
        )}
      >
        {/* 右上角阶段名称 + 状态 + 删除按钮 */}
        <div className="absolute top-2 right-2 flex items-center gap-2">
          <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-emerald-100 text-emerald-700">
            {currentStage?.label}
          </span>
          <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium', statusColor.bg, statusColor.text)}>
            {STATUS_LABELS[stageStatus as StageStatus]}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.(issue);
            }}
            className="p-1 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors opacity-0 group-hover:opacity-100"
            title="删除"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>

        {/* Issue ID 标签 */}
        <div className="flex items-center gap-2 mb-2">
          <span className="inline-flex items-center px-2 py-0.5 bg-blue-50 text-blue-600 text-xs font-medium rounded-full">
            #{issueNumber}
          </span>
        </div>

        <h4 className="font-semibold text-slate-800 text-sm line-clamp-2 leading-snug">
          {issue.title}
        </h4>

        <div className="mt-2">
          <span className="text-xs text-slate-400">
            {issue.createdAt.toLocaleDateString('zh-CN')}
          </span>
        </div>
      </div>
    </div>
  );
}
