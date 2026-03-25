import { useState, useEffect, useCallback } from 'react';
import type { Issue } from '@/types';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { IssueDetail } from '@/components/issue/IssueDetail';
import { issueApi } from '@/lib/api';

export function Home() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  // 加载 Issue 列表
  const loadIssues = useCallback(async () => {
    try {
      setLoading(true);
      const data = await issueApi.getAll();
      setIssues(data);
    } catch (err) {
      console.error('Failed to load issues:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  const handleIssueClick = (issue: Issue) => {
    setSelectedIssue(issue);
  };

  const handleCloseDetail = () => {
    setSelectedIssue(null);
  };

  const handleApprove = () => {
    if (!selectedIssue) return;
    // TODO: 实现通过逻辑
    console.log('Issue approved:', selectedIssue.id);
    setSelectedIssue(null);
  };

  const handleReject = (reason: string) => {
    if (!selectedIssue) return;
    // TODO: 实现打回逻辑
    console.log('Issue rejected:', selectedIssue.id, reason);
    setSelectedIssue(null);
  };

  const handleTrigger = () => {
    if (!selectedIssue) return;
    // TODO: 实现触发 AI 更新逻辑
    console.log('Trigger AI update for:', selectedIssue.id);
  };

  // 新建 Issue 后刷新列表
  const handleIssueCreated = (issue: Issue) => {
    setIssues((prev) => [...prev, issue]);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50">
        <div className="text-slate-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* 泳道图区域 */}
      <div className={`flex-1 transition-all ${selectedIssue ? 'mr-0' : ''}`}>
        <KanbanBoard
          issues={issues}
          onIssueClick={handleIssueClick}
          onIssueCreated={handleIssueCreated}
          className="h-full"
        />
      </div>

      {/* Issue 详情侧边栏 */}
      {selectedIssue && (
        <div className="w-[500px] border-l border-gray-200 flex flex-col">
          <IssueDetail
            issue={selectedIssue}
            onClose={handleCloseDetail}
            onApprove={handleApprove}
            onReject={handleReject}
            onTrigger={handleTrigger}
            className="flex-1"
          />
        </div>
      )}
    </div>
  );
}
