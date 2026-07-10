import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export function ThinkingIndicator({ status }) {
  const messages = {
    'thinking': 'Reasoning...',
    'searching': 'Searching the web...',
    'remembering': 'Recalling memory...',
    'coding': 'Writing code...',
    'analyzing': 'Analyzing...',
  };
  const label = messages[status] || 'Thinking...';

  return (
    <AnimatePresence>
      {status && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-2 px-4 py-2 mx-4 rounded-xl bg-indigo-950/60 border border-indigo-500/20 backdrop-blur-sm w-fit"
        >
          <Sparkles size={12} className="text-indigo-400 animate-pulse" />
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-indigo-400"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1, delay: i * 0.15, repeat: Infinity }}
              />
            ))}
          </div>
          <span className="text-xs text-indigo-300 font-medium">{label}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
