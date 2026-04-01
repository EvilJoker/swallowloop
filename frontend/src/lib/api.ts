/**
 * API 封装 - 调用后端 REST API
 */
import type { Issue, Stage, IssueStatus } from '@/types';

const API_BASE = '/api';

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = 'Request failed';
    try {
      const error = await response.json();
      errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error);
    } catch {
      // 响应体不是 JSON，使用状态码作为错误信息
      errorMessage = `HTTP ${response.status}`;
    }
    throw new ApiError(response.status, errorMessage);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  const data = JSON.parse(text);
  // 后端 API 返回格式可能是 {"issues": [...]}（列表）或 {"issue": {...}}（单个）
  if (data && typeof data === 'object') {
    if ('issues' in data && Array.isArray(data.issues)) {
      return data.issues as T;
    }
    if ('issue' in data && data.issue) {
      return data.issue as T;
    }
  }
  return data as T;
}

// 辅助函数：将 API 返回的日期字符串转换为 Date 对象
function parseIssueDates(issue: any): Issue {
  if (!issue || typeof issue !== 'object') {
    throw new Error('Invalid issue data');
  }

  const result: any = {
    ...issue,
    createdAt: issue.createdAt ? new Date(issue.createdAt) : new Date(),
    archivedAt: issue.archivedAt ? new Date(issue.archivedAt) : undefined,
    discardedAt: issue.discardedAt ? new Date(issue.discardedAt) : undefined,
  };

  if (issue.stages && typeof issue.stages === 'object') {
    result.stages = Object.fromEntries(
      Object.entries(issue.stages).map(([key, stage]: [string, any]) => [
        key,
        {
          ...stage,
          startedAt: stage.startedAt ? new Date(stage.startedAt) : undefined,
          completedAt: stage.completedAt ? new Date(stage.completedAt) : undefined,
          comments: Array.isArray(stage.comments)
            ? stage.comments.map((c: any) => ({
                ...c,
                createdAt: c.createdAt ? new Date(c.createdAt) : new Date(),
              }))
            : [],
          documentVersions: Array.isArray(stage.documentVersions)
            ? stage.documentVersions.map((v: any) => ({
                ...v,
                updatedAt: v.updatedAt ? new Date(v.updatedAt) : new Date(),
              }))
            : [],
        },
      ])
    );
  } else {
    result.stages = {};
  }

  return result as Issue;
}

// Issue API
export const issueApi = {
  /**
   * 获取所有 Issue
   */
  async getAll(): Promise<Issue[]> {
    const response = await fetch(`${API_BASE}/issues`);
    const data = await handleResponse<any[]>(response);
    return data.map(parseIssueDates);
  },

  /**
   * 获取单个 Issue
   */
  async getById(id: string): Promise<Issue> {
    const response = await fetch(`${API_BASE}/issues/${id}`);
    const data = await handleResponse<any>(response);
    return parseIssueDates(data);
  },

  /**
   * 创建 Issue
   */
  async create(data: { title: string; description: string }): Promise<Issue> {
    const response = await fetch(`${API_BASE}/issues`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const rawIssue = await handleResponse<any>(response);
    return parseIssueDates(rawIssue);
  },

  /**
   * 更新 Issue
   */
  async update(id: string, data: Partial<Issue>): Promise<Issue> {
    const response = await fetch(`${API_BASE}/issues/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<Issue>(response);
  },

  /**
   * 删除 Issue
   */
  async delete(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/issues/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(response);
  },

  /**
   * 触发 AI 执行
   */
  async trigger(id: string): Promise<{ status: string; issue_id: string; result: any }> {
    const response = await fetch(`${API_BASE}/issues/${id}/trigger`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  /**
   * 审批阶段
   */
  async approveStage(id: string, stage: Stage, comment?: string): Promise<Issue> {
    const response = await fetch(`${API_BASE}/issues/${id}/stages/${stage}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment }),
    });
    return handleResponse<Issue>(response);
  },

  /**
   * 打回阶段
   */
  async rejectStage(id: string, stage: Stage, reason: string): Promise<Issue> {
    const response = await fetch(`${API_BASE}/issues/${id}/stages/${stage}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    return handleResponse<Issue>(response);
  },

  /**
   * 归档 Issue
   */
  async archive(id: string): Promise<Issue> {
    return this.update(id, { status: 'archived' as IssueStatus });
  },

  /**
   * 废弃 Issue
   */
  async discard(id: string): Promise<Issue> {
    return this.update(id, { status: 'discarded' as IssueStatus });
  },
};

// WebSocket 执行日志
export function createExecutionLogSocket(issueId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/execution/${issueId}`);
}

// DeerFlow Status API
export interface DeerFlowStatus {
  status: 'online' | 'offline';
  version: string | null;
  model_name: string | null;
  model_display_name: string | null;
  minimax_used: number;
  minimax_quota: number;
  minimax_next_refresh: string | null;
  base_url: string;
  data_dir: string;
  active_threads: number;
}

export const deerflowApi = {
  /**
   * 获取 DeerFlow 状态
   */
  async getStatus(): Promise<DeerFlowStatus> {
    const response = await fetch(`${API_BASE}/deerflow/status`);
    return handleResponse<DeerFlowStatus>(response);
  },
};
