import React, { useState, useEffect } from 'react';
import { readClipboardText, getActiveWindowTitle } from '../../core/desktopApi';

export function FloatingInputBar({ onSend }) {
  const [input, setInput] = useState('');
  const [activeWindow, setActiveWindow] = useState('');
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    // Poll focus state for context
    const interval = setInterval(async () => {
      const title = await getActiveWindowTitle();
      setActiveWindow(title);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput('');
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setInput(prev => prev + ` [File: ${files[0].name}] `);
    }
  };

  const insertClipboard = async () => {
    const text = await readClipboardText();
    if (text) {
      setInput(prev => prev + " " + text);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 w-[600px] z-50 transition-all duration-300 ${
        dragging ? 'scale-105 border-indigo-500 shadow-indigo-500/20' : 'border-white/10'
      }`}
    >
      {/* Context awareness badge */}
      {activeWindow && (
        <div className="text-[10px] text-zinc-400 mb-1 px-3 py-1 rounded-full bg-black/40 border border-white/5 w-max mx-auto backdrop-blur-md">
          Context: Focused on <span className="text-cyan-400 font-semibold">{activeWindow}</span>
        </div>
      )}

      {/* Glassmorphic input panel */}
      <div className="flex items-center gap-2 p-3 bg-zinc-900/60 backdrop-blur-2xl rounded-2xl border border-white/10 shadow-2xl">
        <button
          onClick={insertClipboard}
          title="Paste context"
          className="p-2 hover:bg-white/5 rounded-lg text-zinc-400 hover:text-white transition-colors"
        >
          📋
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask MSA Agent anything... (Drag files here)"
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          className="flex-1 bg-transparent text-sm text-white placeholder-zinc-500 focus:outline-none"
        />
        <button
          onClick={handleSend}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95"
        >
          Send
        </button>
      </div>
    </div>
  );
}
