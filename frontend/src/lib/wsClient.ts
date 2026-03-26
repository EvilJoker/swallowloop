import { useIssueStore } from '@/store/issueStore';

let ws: WebSocket | null = null;

export function initIssueWebSocket() {
  // 防止重复连接（包括 CONNECTING 状态）
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws/issues`);

  ws.onopen = () => {
    useIssueStore.getState().setConnected(true);
    console.log('WebSocket connected');
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    const store = useIssueStore.getState();

    switch (msg.type) {
      case 'issue_created':
        store.addIssue(parseIssueDates(msg.issue));
        break;
      case 'issue_updated':
        store.updateIssue(parseIssueDates(msg.issue));
        break;
      case 'issue_deleted':
        store.removeIssue(msg.issue_id);
        break;
    }
  };

  ws.onclose = () => {
    useIssueStore.getState().setConnected(false);
    setTimeout(() => initIssueWebSocket(), 3000);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
}

// 辅助函数：将 API 返回的日期字符串转换为 Date 对象
function parseIssueDates(issue: any): any {
  if (!issue || typeof issue !== 'object') {
    return issue;
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
        },
      ])
    );
  } else {
    result.stages = {};
  }

  return result;
}
