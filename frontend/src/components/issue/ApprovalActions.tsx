import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Check, X, Send, Zap } from 'lucide-react';

interface ApprovalActionsProps {
  onApprove?: () => void;
  onReject?: (reason: string) => void;
  onTrigger?: () => void;
  className?: string;
}

export function ApprovalActions({ onApprove, onReject, onTrigger, className }: ApprovalActionsProps) {
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const handleReject = () => {
    if (rejectReason.trim()) {
      onReject?.(rejectReason);
      setRejectReason('');
      setShowRejectInput(false);
    }
  };

  return (
    <div className={cn('space-y-3', className)}>
      {showRejectInput ? (
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="请输入打回原因..."
            className="w-full p-3 bg-white border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-slate-800 placeholder:text-slate-400"
            rows={3}
          />
          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={() => {
                setShowRejectInput(false);
                setRejectReason('');
              }}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-200 rounded-lg transition-colors font-medium"
            >
              取消
            </button>
            <button
              onClick={handleReject}
              disabled={!rejectReason.trim()}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-red-500 text-white hover:bg-red-600 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-3.5 w-3.5" />
              确认打回
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button
            onClick={onApprove}
            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-emerald-500 text-white hover:bg-emerald-600 rounded-lg transition-colors text-sm font-medium shadow-sm"
          >
            <Check className="h-4 w-4" />
            通过
          </button>
          <button
            onClick={() => setShowRejectInput(!showRejectInput)}
            className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-white text-slate-600 hover:bg-slate-50 border border-slate-200 rounded-lg transition-colors text-sm font-medium"
          >
            <X className="h-4 w-4" />
            打回
          </button>
        </div>
      )}

      {onTrigger && !showRejectInput && (
        <button
          onClick={onTrigger}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors text-xs font-medium"
        >
          <Zap className="h-3.5 w-3.5" />
          手动触发 AI 更新
        </button>
      )}
    </div>
  );
}
