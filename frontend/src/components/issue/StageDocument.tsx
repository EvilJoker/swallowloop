import { useState } from 'react';
import { cn } from '@/lib/utils';

interface StageDocumentProps {
  content: string;
  onSave?: (content: string) => void;
  readOnly?: boolean;
  className?: string;
}

export function StageDocument({ content, onSave, readOnly = false, className }: StageDocumentProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);

  const handleSave = () => {
    onSave?.(editContent);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditContent(content);
    setIsEditing(false);
  };

  if (isEditing && !readOnly) {
    return (
      <div className={cn('flex flex-col h-full', className)}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900">阶段文档</h3>
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-md transition-colors"
            >
              保存
            </button>
          </div>
        </div>
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="flex-1 w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          placeholder="输入 Markdown 内容..."
        />
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-gray-900">阶段文档</h3>
        {!readOnly && (
          <button
            onClick={() => setIsEditing(true)}
            className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
          >
            编辑
          </button>
        )}
      </div>
      <div className="flex-1 p-4 bg-gray-50 rounded-lg overflow-auto">
        <div className="prose prose-sm max-w-none">
          {content.split('\n').map((line, i) => (
            <p key={i} className="mb-2 text-gray-700">{line || '\u00A0'}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
