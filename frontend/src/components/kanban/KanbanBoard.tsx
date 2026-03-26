import { useState } from 'react';
import { Plus, AlertTriangle } from 'lucide-react';
import type { Issue, Stage } from '@/types';
import { STAGES } from '@/types';
import { KanbanLane } from './KanbanLane';
import { NewIssueDialog } from '@/components/issue/NewIssueDialog';
import { issueApi } from '@/lib/api';

interface KanbanBoardProps {
  issues: Issue[];
  onIssueClick?: (issue: Issue) => void;
  onIssueCreated?: (issue: Issue) => void;
  onIssueDeleted?: () => void;
  className?: string;
}

function DeleteConfirmDialog({
  issueTitle,
  onConfirm,
  onCancel,
}: {
  issueTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-xl p-6 shadow-xl max-w-sm w-full mx-4">
        <div className="flex items-center gap-3 text-red-600 mb-3">
          <AlertTriangle className="h-6 w-6" />
          <span className="font-semibold text-lg">确认删除</span>
        </div>
        <p className="text-slate-600 mb-5">确定删除「{issueTitle}」？此操作不可撤销。</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

export function KanbanBoard({ issues, onIssueClick, onIssueCreated, onIssueDeleted, className }: KanbanBoardProps) {
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Issue | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 按阶段分组
  const issuesByStage = STAGES.reduce<Record<Stage, Issue[]>>((acc, stage) => {
    acc[stage.key] = issues.filter(
      (issue) => issue.status === 'active' && issue.currentStage === stage.key
    );
    return acc;
  }, {} as Record<Stage, Issue[]>);

  const handleIssueCreated = (issue: Issue) => {
    onIssueCreated?.(issue);
    setShowNewDialog(false);
  };

  const handleDelete = (issue: Issue) => {
    setDeleteTarget(issue);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await issueApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      // 通知父组件刷新数据
      onIssueDeleted?.();
    } catch (err) {
      console.error('删除失败:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className={className}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
        <h2 className="font-semibold text-slate-800">泳道图</h2>
        <button
          onClick={() => setShowNewDialog(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 text-white hover:bg-blue-600 rounded-lg transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          新建 Issue
        </button>
      </div>

      {/* 泳道图头部 - 固定7列 */}
      <div className="flex bg-slate-100 border-b border-slate-200">
        {STAGES.map((stage) => (
          <div
            key={stage.key}
            className="w-[200px] min-w-[200px] px-3 py-2.5 border-r border-slate-200 last:border-r-0"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-slate-700 text-sm">{stage.label}</h3>
              <span className="text-xs text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded-full">
                {issuesByStage[stage.key].length}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* 泳道内容 */}
      <div className="flex bg-slate-50 overflow-x-auto">
        {STAGES.map((stage) => (
          <KanbanLane
            key={stage.key}
            issues={issuesByStage[stage.key]}
            onIssueClick={onIssueClick}
            onIssueDelete={handleDelete}
            className="border-r border-slate-100 last:border-r-0"
          />
        ))}
      </div>

      {/* 新建 Issue 对话框 */}
      {showNewDialog && (
        <NewIssueDialog
          onClose={() => setShowNewDialog(false)}
          onCreated={handleIssueCreated}
        />
      )}

      {/* 删除确认对话框 */}
      {deleteTarget && !isDeleting && (
        <DeleteConfirmDialog
          issueTitle={deleteTarget.title}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {/* 删除中状态 */}
      {isDeleting && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="text-white text-lg">删除中...</div>
        </div>
      )}
    </div>
  );
}
