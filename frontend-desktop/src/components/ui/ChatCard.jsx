import React, { useState } from 'react';
import { useStore } from '../../core/stateStore';

function renderMarkdown(content) {
  if (!content) return "";
  
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
  let parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const textBefore = content.substring(lastIndex, match.index);
    const lang = match[1] || 'code';
    const code = match[2];
    
    if (textBefore) {
      parts.push(<span key={lastIndex} className="whitespace-pre-wrap">{textBefore}</span>);
    }
    
    parts.push(
      <div key={match.index} className="my-3 border border-white/10 rounded-lg overflow-hidden bg-black/60 font-mono text-[11px] text-zinc-300">
        <div className="flex justify-between items-center px-3 py-1.5 bg-white/5 border-b border-white/5 text-[9px] uppercase tracking-wider text-zinc-500 font-bold select-none">
          <span>{lang}</span>
          <button 
            onClick={() => navigator.clipboard.writeText(code)} 
            className="hover:text-white transition-colors cursor-pointer"
          >
            Copy
          </button>
        </div>
        <pre className="p-3 overflow-x-auto whitespace-pre"><code>{code}</code></pre>
      </div>
    );
    
    lastIndex = codeBlockRegex.lastIndex;
  }
  
  const textAfter = content.substring(lastIndex);
  if (textAfter) {
    parts.push(<span key={lastIndex} className="whitespace-pre-wrap">{textAfter}</span>);
  }
  
  return parts.length > 0 ? parts : content;
}

export function ChatCard({ card }) {
  const { updateCard } = useStore();
  const [dragging, setDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    if (e.target.closest('.card-drag-handle')) {
      setDragging(true);
      setDragOffset({
        x: e.clientX - card.x,
        y: e.clientY - card.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (!dragging) return;
    updateCard(card.id, {
      x: e.clientX - dragOffset.x,
      y: e.clientY - dragOffset.y
    });
  };

  const handleMouseUp = () => {
    setDragging(false);
  };

  const headerColors = {
    user: 'border-cyan-500/20 bg-cyan-950/20 text-cyan-400',
    planner: 'border-blue-500/20 bg-blue-950/20 text-blue-400',
    coder: 'border-emerald-500/20 bg-emerald-950/20 text-emerald-400',
    researcher: 'border-yellow-500/20 bg-yellow-950/20 text-yellow-400',
    browser: 'border-indigo-500/20 bg-indigo-950/20 text-indigo-400',
    validator: 'border-violet-500/20 bg-violet-950/20 text-violet-400'
  };

  const themeClass = headerColors[card.role] || 'border-white/10 bg-zinc-900/40 text-white';

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        left: `${card.x}px`,
        top: `${card.y}px`,
        position: 'absolute'
      }}
      className={`w-[360px] border rounded-2xl shadow-xl overflow-hidden backdrop-blur-md transition-all duration-300 ${themeClass} ${
        dragging ? 'shadow-indigo-500/25 border-indigo-500/40 scale-102' : ''
      }`}
    >
      {/* Header / Drag Handle */}
      <div
        onMouseDown={handleMouseDown}
        className="card-drag-handle flex items-center justify-between p-3 border-b border-white/5 cursor-grab active:cursor-grabbing text-xs font-semibold select-none"
      >
        <span className="capitalize">{card.role} Engine</span>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
        </div>
      </div>

      {/* Body Content */}
      <div className="p-4 text-xs leading-relaxed font-medium">
        {renderMarkdown(card.content)}
      </div>
    </div>
  );
}
