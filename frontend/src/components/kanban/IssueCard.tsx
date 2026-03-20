import { cn } from '@/lib/utils';
import type { Issue, StageStatus } from '@/types';

interface IssueCardProps {
  issue: Issue;
  onClick?: () => void;
  className?: string;
}

const STATUS_CONFIG: Record<StageStatus, { label: string; dot: string; badge: string; border: string }> = {
  pending: {
    label: '待审批',
    dot: 'bg-amber-400',
    badge: 'bg-amber-50 text-amber-600 border-amber-100',
    border: 'border-l-amber-400',
  },
  approved: {
    label: '已通过',
    dot: 'bg-emerald-400',
    badge: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    border: 'border-l-emerald-400',
  },
  rejected: {
    label: '已打回',
    dot: 'bg-purple-400',
    badge: 'bg-purple-50 text-purple-600 border-purple-100',
    border: 'border-l-purple-400',
  },
  running: {
    label: '运行中',
    dot: 'bg-blue-400',
    badge: 'bg-blue-50 text-blue-600 border-blue-100',
    border: 'border-l-blue-400',
  },
  error: {
    label: '异常',
    dot: 'bg-red-400',
    badge: 'bg-red-50 text-red-600 border-red-100',
    border: 'border-l-red-400',
  },
};

export function IssueCard({ issue, onClick, className }: IssueCardProps) {
  const currentStageState = issue.stages[issue.currentStage];
  const config = STATUS_CONFIG[currentStageState.status];
  const issueNumber = issue.id.replace('issue-', '');

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full p-3 bg-white rounded-xl border border-slate-200 border-l-4 shadow-sm text-left',
        'hover:shadow-md hover:border-slate-300 hover:-translate-y-0.5 transition-all cursor-pointer',
        config.border,
        className
      )}
    >
      {/* Issue ID 标签 */}
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center px-2 py-0.5 bg-blue-50 text-blue-600 text-xs font-medium rounded-full">
          #{issueNumber}
        </span>
      </div>

      <h4 className="font-medium text-slate-800 text-sm mb-2 line-clamp-2 leading-snug">
        {issue.title}
      </h4>

      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-slate-400">
          {issue.createdAt.toLocaleDateString('zh-CN')}
        </span>
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
            config.badge
          )}
        >
          <span className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
          {config.label}
        </span>
      </div>
    </button>
  );
}
