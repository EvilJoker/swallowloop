import { create } from 'zustand';
import type { Issue } from '@/types';

interface IssueStore {
  // State
  issues: Issue[];
  loading: boolean;
  connected: boolean;
  selectedIssueId: string | null;

  // Actions
  setIssues: (issues: Issue[]) => void;
  updateIssue: (issue: Issue) => void;
  addIssue: (issue: Issue) => void;
  setLoading: (loading: boolean) => void;
  setConnected: (connected: boolean) => void;
  setSelectedIssueId: (id: string | null) => void;
}

export const useIssueStore = create<IssueStore>((set) => ({
  issues: [],
  loading: true,
  connected: false,
  selectedIssueId: null,
  setIssues: (issues) => set({ issues }),
  updateIssue: (issue) =>
    set((state) => ({
      issues: state.issues.map((i) => (i.id === issue.id ? issue : i)),
    })),
  addIssue: (issue) => set((state) => ({ issues: [...state.issues, issue] })),
  setLoading: (loading) => set({ loading }),
  setConnected: (connected) => set({ connected }),
  setSelectedIssueId: (selectedIssueId) => set({ selectedIssueId }),
}));
