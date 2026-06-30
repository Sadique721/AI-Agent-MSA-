import React, { useState } from 'react';
import { useStore } from '../../core/stateStore';

export function ChatCard({ card }) {
  const { updateCard } = useStore();
  const [dragging, setDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    // Only allow drag from header
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
      className={`w-[320px] bg-zinc-900/40 border border-white/10 rounded-2xl shadow-xl overflow-hidden backdrop-blur-md transition-shadow select-none ${
        dragging ? 'shadow-indigo-500/10 border-indigo-500/30' : ''
      }`}
    >
      {/* Header / Drag Handle */}
      <div
        onMouseDown={handleMouseDown}
        className="card-drag-handle flex items-center justify-between p-3 bg-white/5 border-b border-white/5 cursor-grab active:cursor-grabbing text-xs text-zinc-400 font-semibold"
      >
        <span className="capitalize">{card.role} Card</span>
        <div className="flex gap-1">
          <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
          <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
        </div>
      </div>

      {/* Body Content */}
      <div className="p-4 text-xs text-white leading-relaxed whitespace-pre-line font-medium">
        {card.content}
      </div>
    </div>
  );
}
