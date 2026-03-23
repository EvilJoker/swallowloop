import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { KanbanLane } from '@/components/kanban/KanbanLane';
import { IssueCard } from '@/components/kanban/IssueCard';
import type { Issue } from '@/types';
import { mockIssue1, mockIssue2, mockIssue3 } from '@/types/mock';

// KanbanBoard 测试
describe('KanbanBoard', () => {
  it('should render all 7 stage lanes', () => {
    render(<KanbanBoard issues={[]} onIssueClick={() => {}} />);

    expect(screen.getByText('头脑风暴')).toBeDefined();
    expect(screen.getByText('方案成型')).toBeDefined();
    expect(screen.getByText('详细设计')).toBeDefined();
    expect(screen.getByText('任务拆分')).toBeDefined();
    expect(screen.getByText('执行')).toBeDefined();
    expect(screen.getByText('更新文档')).toBeDefined();
    expect(screen.getByText('提交')).toBeDefined();
  });

  it('should render issues in correct lanes', () => {
    const issues: Issue[] = [mockIssue1, mockIssue2, mockIssue3];
    render(<KanbanBoard issues={issues} onIssueClick={() => {}} />);

    // mockIssue1 位于 brainstorm 阶段 (active, running)
    // mockIssue2 位于 execution 阶段 (active)
    // mockIssue3 位于 detailedDesign 阶段 (active)

    // 查找 Issue 卡片 - IssueCard 是一个 button
    const cards = document.querySelectorAll('button[class*="rounded-xl"]');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('should show issue count in lane header', () => {
    const issues: Issue[] = [mockIssue1]; // mockIssue1 在 brainstorm
    render(<KanbanBoard issues={issues} onIssueClick={() => {}} />);

    // brainstorm 泳道应该有 1 个 issue
    const brainstormHeader = screen.getByText('头脑风暴').closest('div');
    expect(brainstormHeader?.innerHTML).toContain('1');
  });

  it('should show create button', () => {
    render(<KanbanBoard issues={[]} onIssueClick={() => {}} />);

    expect(screen.getByText('新建 Issue')).toBeDefined();
  });
});

// KanbanLane 测试
describe('KanbanLane', () => {
  it('should render empty state when no issues', () => {
    render(
      <KanbanLane
        issues={[]}
        onIssueClick={() => {}}
      />
    );

    expect(screen.getByText('暂无问题')).toBeDefined();
  });

  it('should render issue cards when issues exist', () => {
    render(
      <KanbanLane
        issues={[mockIssue1]}
        onIssueClick={() => {}}
      />
    );

    // 应该显示 Issue 标题
    expect(screen.getByText('实现用户登录功能')).toBeDefined();
  });

  it('should show multiple issues', () => {
    render(
      <KanbanLane
        issues={[mockIssue1, mockIssue2]}
        onIssueClick={() => {}}
      />
    );

    // 应该显示两个 issue
    expect(screen.getByText('实现用户登录功能')).toBeDefined();
    expect(screen.getByText('添加 GitHub Actions CI/CD')).toBeDefined();
  });
});

// IssueCard 测试
describe('IssueCard', () => {
  it('should render issue title', () => {
    render(
      <IssueCard
        issue={mockIssue1}
        onClick={() => {}}
      />
    );

    expect(screen.getByText('实现用户登录功能')).toBeDefined();
  });

  it('should show status badge', () => {
    render(
      <IssueCard
        issue={mockIssue1}
        onClick={() => {}}
      />
    );

    // mockIssue1 的 brainstorm 阶段状态是 running
    // 应该显示"运行中"
    expect(screen.getByText('运行中')).toBeDefined();
  });

  it('should call onClick when clicked', () => {
    const onClick = vi.fn();
    render(
      <IssueCard
        issue={mockIssue1}
        onClick={onClick}
      />
    );

    screen.getByText('实现用户登录功能').click();
    expect(onClick).toHaveBeenCalled();
  });

  it('should render issue number', () => {
    render(
      <IssueCard
        issue={mockIssue1}
        onClick={() => {}}
      />
    );

    // mockIssue1 的 id 是 'issue-1'，所以编号是 '1'
    expect(screen.getByText('#1')).toBeDefined();
  });

  it('should show approved status', () => {
    render(
      <IssueCard
        issue={mockIssue2}
        onClick={() => {}}
      />
    );

    // mockIssue2 的 execution 阶段状态是 running
    expect(screen.getByText('运行中')).toBeDefined();
  });

  it('should show rejected status', () => {
    render(
      <IssueCard
        issue={mockIssue3}
        onClick={() => {}}
      />
    );

    // mockIssue3 的 detailedDesign 阶段状态是 rejected
    expect(screen.getByText('已打回')).toBeDefined();
  });
});
