import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { MainContent } from '@/components/layout/MainContent';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { IssueDetail } from '@/components/issue/IssueDetail';
import { Overview } from '@/pages/Overview';
import { Settings } from '@/pages/Settings';
import { Archive } from '@/pages/Archive';
import type { Issue } from '@/types';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { issueApi } from '@/lib/api';
import { useIssueStore } from '@/store/issueStore';
import { initIssueWebSocket } from '@/lib/wsClient';

type Page = 'home' | 'overview' | 'archive' | 'settings';

interface Tab {
  id: string;
  type: 'kanban' | 'issue';
  title: string;
  issue?: Issue;
}

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [tabs, setTabs] = useState<Tab[]>([{ id: 'kanban', type: 'kanban', title: '泳道图' }]);
  const [activeTabId, setActiveTabId] = useState('kanban');

  // 使用 Zustand store
  const issues = useIssueStore((state) => state.issues);
  const setIssues = useIssueStore((state) => state.setIssues);
  const setLoading = useIssueStore((state) => state.setLoading);
  const setBackendConnected = useIssueStore((state) => state.setBackendConnected);

  // 心跳检查后端状态（每15秒）
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch('/health');
        setBackendConnected(res.ok);
      } catch {
        setBackendConnected(false);
      }
    };

    // 立即检查一次
    checkBackend();
    // 每15秒检查一次
    const interval = setInterval(checkBackend, 15000);
    return () => clearInterval(interval);
  }, [setBackendConnected]);

  // 初始化 WebSocket 和加载数据
  useEffect(() => {
    initIssueWebSocket();
    setLoading(true);
    issueApi.getAll().then((data) => {
      setIssues(data);
      setLoading(false);
    });
  }, [setIssues, setLoading]);

  // 打开 Issue 详情 Tab
  const openIssueTab = (issue: Issue) => {
    const existingTab = tabs.find((t) => t.type === 'issue' && t.issue?.id === issue.id);
    if (existingTab) {
      setActiveTabId(existingTab.id);
      return;
    }
    const newTab: Tab = {
      id: `issue-${issue.id}`,
      type: 'issue',
      title: `#${issue.id.replace('issue-', '')} ${issue.title.length > 12 ? issue.title.slice(0, 12) + '...' : issue.title}`,
      issue,
    };
    setTabs([...tabs, newTab]);
    setActiveTabId(newTab.id);
  };

  // 关闭 Tab
  const closeTab = (tabId: string) => {
    if (tabId === 'kanban') return;
    const newTabs = tabs.filter((t) => t.id !== tabId);
    setTabs(newTabs);
    if (activeTabId === tabId) {
      setActiveTabId('kanban');
    }
  };

  // 刷新 Issue 数据
  const refreshIssue = async (issueId: string) => {
    try {
      const updated = await issueApi.getById(issueId);
      useIssueStore.getState().updateIssue(updated);
      // 同时更新 tab 中的 issue
      setTabs((prev) =>
        prev.map((t) => (t.issue?.id === issueId ? { ...t, issue: updated } : t))
      );
    } catch (err) {
      console.error('Failed to refresh issue:', err);
    }
  };

  // 新建 Issue 后的回调
  const handleIssueCreated = (issue: Issue) => {
    useIssueStore.getState().addIssue(issue);
  };

  // 渲染当前 Tab 内容
  const renderTabContent = () => {
    const activeTab = tabs.find((t) => t.id === activeTabId);
    if (!activeTab) return <KanbanBoard issues={issues} onIssueClick={openIssueTab} onIssueCreated={handleIssueCreated} />;

    switch (activeTab.type) {
      case 'kanban':
        return <KanbanBoard issues={issues} onIssueClick={openIssueTab} onIssueCreated={handleIssueCreated} />;
      case 'issue':
        return activeTab.issue ? (
          <IssueDetail
            issue={activeTab.issue}
            onApprove={async () => {
              if (!activeTab.issue) return;
              try {
                await issueApi.approveStage(activeTab.issue.id, activeTab.issue.currentStage);
                await refreshIssue(activeTab.issue.id);
                closeTab(activeTab.id);
              } catch (err) {
                console.error('Failed to approve:', err);
              }
            }}
            onReject={async (reason) => {
              if (!activeTab.issue) return;
              try {
                await issueApi.rejectStage(activeTab.issue.id, activeTab.issue.currentStage, reason);
                await refreshIssue(activeTab.issue.id);
                closeTab(activeTab.id);
              } catch (err) {
                console.error('Failed to reject:', err);
              }
            }}
            onTrigger={async () => {
              if (!activeTab.issue) return;
              try {
                await issueApi.trigger(activeTab.issue.id);
                await refreshIssue(activeTab.issue.id);
              } catch (err) {
                console.error('Failed to trigger:', err);
              }
            }}
          />
        ) : null;
      default:
        return null;
    }
  };

  // 渲染页面
  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return (
          <div className="h-full flex flex-col">
            {/* Tab 区 - 扁平化分段控制器样式 */}
            <div className="flex items-center px-3 py-2 bg-slate-100">
              <div className="flex gap-1 p-1 bg-white rounded-lg shadow-sm">
                {tabs.map((tab, index) => (
                  <div key={tab.id} className="flex items-center">
                    {index > 0 && <div className="w-px h-4 bg-slate-200 mx-1" />}
                    <div
                      onClick={() => setActiveTabId(tab.id)}
                      className={cn(
                        'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md cursor-pointer transition-colors',
                        activeTabId === tab.id
                          ? 'bg-blue-500 text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-800'
                      )}
                    >
                      <span>{tab.title}</span>
                      {tab.type === 'issue' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            closeTab(tab.id);
                          }}
                          className={cn(
                            'p-0.5 rounded transition-colors',
                            activeTabId === tab.id
                              ? 'hover:bg-blue-600 text-blue-200 hover:text-white'
                              : 'text-slate-400 hover:text-slate-600 hover:bg-slate-200'
                          )}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            {/* 内容区 */}
            <div className="flex-1 overflow-auto">
              {renderTabContent()}
            </div>
          </div>
        );
      case 'overview':
        return <Overview />;
      case 'archive':
        return <Archive />;
      case 'settings':
        return <Settings />;
      default:
        return <Overview />;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
        <MainContent className="flex-1 overflow-hidden">
          {renderPage()}
        </MainContent>
      </div>
    </div>
  );
}

export default App;
