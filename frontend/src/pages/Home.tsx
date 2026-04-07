import { useEffect } from 'react';
import type { Issue } from '@/types';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { IssueDetail } from '@/components/issue/IssueDetail';
import { issueApi } from '@/lib/api';
import { useIssueStore } from '@/store/issueStore';
import { initIssueWebSocket } from '@/lib/wsClient';

export function Home() {
  const issues = useIssueStore((state) => state.issues);
  const loading = useIssueStore((state) => state.loading);
  const selectedIssueId = useIssueStore((state) => state.selectedIssueId);
  const setIssues = useIssueStore((state) => state.setIssues);
  const setLoading = useIssueStore((state) => state.setLoading);
  const setSelectedIssueId = useIssueStore((state) => state.setSelectedIssueId);

  // 根据 selectedIssueId 查找完整的 issue 对象
  const selectedIssue = issues.find((issue) => issue.id === selectedIssueId) ?? null;

  // 初始化 WebSocket 和加载数据
  useEffect(() => {
    // 初始化 WebSocket
    initIssueWebSocket();

    // 加载初始数据
    setLoading(true);
    issueApi.getAll().then((data) => {
      setIssues(data);
      setLoading(false);
    });
  }, [setIssues, setLoading]);

  const handleIssueClick = (issue: Issue) => {
    setSelectedIssueId(issue.id);
  };

  const handleCloseDetail = () => {
    setSelectedIssueId(null);
  };

  const handleIssueCreated = (_issue: Issue) => {
    // WebSocket 会自动更新，不需要手动处理
  };

  const handleIssueDeleted = () => {
    // 删除成功后重新加载数据
    issueApi.getAll().then((data) => {
      setIssues(data);
    });
  };

  const handleRefresh = () => {
    // 优先刷新选中的 issue（通过 getById 获取最新状态）
    if (selectedIssueId) {
      issueApi.getById(selectedIssueId).then((updatedIssue) => {
        useIssueStore.getState().updateIssue(updatedIssue);
      });
    } else {
      issueApi.getAll().then((data) => {
        setIssues(data);
      });
    }
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
          onIssueDeleted={handleIssueDeleted}
          className="h-full"
        />
      </div>

      {/* Issue 详情侧边栏 */}
      {selectedIssue && (
        <div className="w-[500px] border-l border-gray-200 flex flex-col">
          <IssueDetail
            issue={selectedIssue}
            onClose={handleCloseDetail}
            onRefresh={handleRefresh}
            className="flex-1"
          />
        </div>
      )}
    </div>
  );
}
