import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Issue } from '@/types';
import { STAGES, STATUS_LABELS } from '@/types';
import { PipelineDetail } from './PipelineDetail';

interface IssueDetailProps {
  issue: Issue;
  onClose?: () => void;
  onRefresh?: () => void;
  className?: string;
}

export function IssueDetail({
  issue,
  onClose,
  onRefresh,
  className,
}: IssueDetailProps) {
  const currentStageState = issue.stages[issue.currentStage];
  const stageInfo = STAGES.find((s) => s.key === issue.currentStage);

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div>
          <h2 className="font-semibold text-gray-900">{issue.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-gray-500">
              当前阶段：{stageInfo?.label}
            </span>
            <span className="text-sm text-gray-400">|</span>
            <span className="text-sm text-gray-500">
              状态：{STATUS_LABELS[currentStageState.status]}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Tab 切换 - 阶段详情 */}
      <div className="flex border-b border-gray-200 px-4">
        <button
          className={cn(
            'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px text-blue-600 border-blue-600'
          )}
        >
          阶段详情
        </button>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-auto">
        <PipelineDetail issue={issue} onRefresh={onRefresh} />
      </div>
    </div>
  );
}
