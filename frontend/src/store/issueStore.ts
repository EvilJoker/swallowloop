import { create } from 'zustand';
import type { Issue } from '@/types';

interface IssueStore {
  // State
  issues: Issue[];
  loading: boolean;
  connected: boolean;  // WebSocket 连接状态
  backendConnected: boolean;  // 后端 API 连接状态
  selectedIssueId: string | null;

  // Actions
  setIssues: (issues: Issue[]) => void;
  updateIssue: (issue: Issue) => void;
  addIssue: (issue: Issue) => void;
  removeIssue: (issueId: string) => void;
  setLoading: (loading: boolean) => void;
  setConnected: (connected: boolean) => void;
  setBackendConnected: (connected: boolean) => void;
  setSelectedIssueId: (id: string | null) => void;
}

export const useIssueStore = create<IssueStore>((set) => ({
  issues: [],
  loading: true,
  connected: false,
  backendConnected: false,
  selectedIssueId: null,
  setIssues: (issues) => set({ issues }),
  updateIssue: (issue) =>
    set((state) => ({
      issues: state.issues.map((i) => (i.id === issue.id ? issue : i)),
    })),
  addIssue: (issue) =>
    set((state) => {
      // 防止重复添加（WebSocket 消息和 API 响应可能重复）
      if (state.issues.some((i) => i.id === issue.id)) {
        return { issues: [...state.issues] };  // 返回新数组引用确保触发更新
      }
      return { issues: [...state.issues, issue] };
    }),
  removeIssue: (issueId) =>
    set((state) => ({
      issues: state.issues.filter((i) => i.id !== issueId),
    })),
  setLoading: (loading) => set({ loading }),
  setConnected: (connected) => set({ connected }),
  setBackendConnected: (backendConnected) => set({ backendConnected }),
  setSelectedIssueId: (selectedIssueId) => set({ selectedIssueId }),
}));
