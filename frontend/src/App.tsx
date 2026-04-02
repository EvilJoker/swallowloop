import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { MainContent } from '@/components/layout/MainContent';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { IssueDetail } from '@/components/issue/IssueDetail';
import { Overview } from '@/pages/Overview';
import { Archive } from '@/pages/Archive';
import { DeerFlow } from '@/pages/DeerFlow';
import { Repository } from '@/pages/Repository';
import type { Issue } from '@/types';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { issueApi } from '@/lib/api';
import { useIssueStore } from '@/store/issueStore';
import { initIssueWebSocket } from '@/lib/wsClient';

type Page = 'home' | 'overview' | 'archive' | 'deerflow' | 'repository';

interface Tab {
  id: string;
  type: 'kanban' | 'issue';
  title: string;
  issue?: Issue;
}

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');
  const [tabs, setTabs] = useState<Tab[]>([{ id: 'kanban', type: 'kanban', title: '看板' }]);
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

  // 刷新所有 Issues
  const refreshIssues = async () => {
    const data = await issueApi.getAll();
    setIssues(data);
  };

  // 刷新单个 Issue
  const refreshIssue = async (issueId: string) => {
    try {
      const updated = await issueApi.getById(issueId);
      useIssueStore.getState().updateIssue(updated);
      // 同时更新 tab 中的 issue
      setTabs((prev) =>
        prev.map((t) => (t.issue?.id === issueId ? { ...t, issue: updated } : t))
      );
    } catch (err) {
      // ignore
    }
  };

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

  // 新建 Issue 后的回调
  const handleIssueCreated = async (_issue: Issue) => {
    // 直接刷新列表确保 UI 更新（WebSocket 广播在某些情况下可能不可靠）
    await refreshIssues();
  };

  // 渲染当前 Tab 内容
  const renderTabContent = () => {
    const activeTab = tabs.find((t) => t.id === activeTabId);
    if (!activeTab) return <KanbanBoard issues={issues} onIssueClick={openIssueTab} onIssueCreated={handleIssueCreated} onIssueRefresh={refreshIssues} />;

    switch (activeTab.type) {
      case 'kanban':
        return <KanbanBoard issues={issues} onIssueClick={openIssueTab} onIssueCreated={handleIssueCreated} onIssueRefresh={refreshIssues} />;
      case 'issue':
        return activeTab.issue ? (
          <IssueDetail issue={activeTab.issue} onRefresh={() => refreshIssue(activeTab.issue!.id)} />
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
      case 'deerflow':
        return <DeerFlow />;
      case 'repository':
        return <Repository />;
      default:
        return <Overview />;
    }
  };

  // 计算活跃 Issue 数量
  const activeIssueCount = issues.filter((i) => i.status === 'active').length;

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} issueCount={activeIssueCount} />
        <MainContent className="flex-1 overflow-hidden">
          {renderPage()}
        </MainContent>
      </div>
    </div>
  );
}

export default App;
