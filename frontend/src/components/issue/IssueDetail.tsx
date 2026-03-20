import { useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Issue } from '@/types';
import { STAGES, STATUS_LABELS } from '@/types';
import { StageDocument } from './StageDocument';
import { CommentHistory } from './CommentHistory';
import { ApprovalActions } from './ApprovalActions';

interface IssueDetailProps {
  issue: Issue;
  onClose?: () => void;
  onApprove?: () => void;
  onReject?: (reason: string) => void;
  onTrigger?: () => void;
  className?: string;
}

type TabType = 'document' | 'comments';

export function IssueDetail({
  issue,
  onClose,
  onApprove,
  onReject,
  onTrigger,
  className,
}: IssueDetailProps) {
  const [activeTab, setActiveTab] = useState<TabType>('document');
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

      {/* Tab 切换 */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('document')}
          className={cn(
            'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
            activeTab === 'document'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          )}
        >
          阶段文档
        </button>
        <button
          onClick={() => setActiveTab('comments')}
          className={cn(
            'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
            activeTab === 'comments'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          )}
        >
          评论历史 ({currentStageState.comments.length})
        </button>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'document' ? (
          <StageDocument
            content={currentStageState.document}
            readOnly={currentStageState.status !== 'pending'}
          />
        ) : (
          <CommentHistory comments={currentStageState.comments} />
        )}
      </div>

      {/* 操作区 */}
      {currentStageState.status === 'pending' && (
        <div className="p-4 border-t border-gray-200">
          <ApprovalActions
            onApprove={onApprove}
            onReject={onReject}
            onTrigger={onTrigger}
          />
        </div>
      )}
    </div>
  );
}
