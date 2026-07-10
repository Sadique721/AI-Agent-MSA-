import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, Code, Globe, Brain, Database, X } from 'lucide-react';

const QUICK_ACTIONS = [
  { icon: <Code size={14} />, label: 'Generate Spring Boot API', cmd: 'generate a Spring Boot REST API for product management' },
  { icon: <Brain size={14} />, label: 'Explain this code', cmd: 'explain this code step by step' },
  { icon: <Globe size={14} />, label: 'Search web for...', cmd: 'search web for ' },
  { icon: <Database size={14} />, label: 'Recall memory about...', cmd: 'what do you remember about ' },
  { icon: <Zap size={14} />, label: 'Debug this error', cmd: 'debug this error: ' },
];

export function CommandPalette({ isOpen, onClose, onSubmit }) {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filtered = QUICK_ACTIONS.filter(a =>
    a.label.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (cmd) => {
    onSubmit(cmd);
    onClose();
    setQuery('');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.93, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.93, y: -20 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl z-50"
          >
            <div className="bg-zinc-900 border border-white/15 rounded-2xl shadow-2xl shadow-black/80 overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
                <Search size={16} className="text-zinc-500" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Escape') onClose();
                    if (e.key === 'Enter' && query.trim()) handleSelect(query);
                  }}
                  placeholder="Ask anything or select an action..."
                  className="flex-1 bg-transparent text-sm text-white placeholder-zinc-600 outline-none"
                />
                <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">ESC</kbd>
              </div>
              <div className="p-2 max-h-72 overflow-y-auto">
                {filtered.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSelect(action.cmd)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-white/8 transition-colors group"
                  >
                    <span className="text-indigo-400 group-hover:text-indigo-300">{action.icon}</span>
                    <span className="text-sm text-zinc-300 group-hover:text-white">{action.label}</span>
                  </button>
                ))}
                {query && (
                  <button
                    onClick={() => handleSelect(query)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-indigo-600/20 border border-indigo-500/20 transition-colors mt-1"
                  >
                    <Zap size={14} className="text-indigo-400" />
                    <span className="text-sm text-indigo-300">Send: <em className="not-italic font-medium text-white">"{query}"</em></span>
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
