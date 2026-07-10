import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Cpu, User } from 'lucide-react';
import { useState } from 'react';

export function ChatBubble({ message }) {
  const { role, content, streaming, timestamp } = message;
  const isAI = role === 'assistant';
  const [copied, setCopied] = useState(false);

  const copyAll = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 group ${isAI ? 'flex-row' : 'flex-row-reverse'} mb-6 px-2`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold mt-1 ${
        isAI
          ? 'bg-gradient-to-br from-violet-600 to-indigo-700 shadow-lg shadow-violet-900/50'
          : 'bg-gradient-to-br from-zinc-700 to-zinc-800 border border-white/10'
      }`}>
        {isAI ? <Cpu size={14} className="text-white" /> : <User size={14} className="text-zinc-300" />}
      </div>

      {/* Bubble */}
      <div className={`relative max-w-[82%] rounded-2xl px-4 py-3 ${
        isAI
          ? 'bg-zinc-800/60 border border-white/8 backdrop-blur-sm text-zinc-100'
          : 'bg-indigo-600/90 text-white border border-indigo-500/50 shadow-lg shadow-indigo-900/30'
      }`}>
        {/* Rendered content */}
        {isAI ? (
          <ReactMarkdown
            className="prose prose-invert prose-sm max-w-none leading-relaxed"
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const lang = match ? match[1] : '';
                const code = String(children).replace(/\n$/, '');

                if (!inline && lang) {
                  return (
                    <div className="my-3 rounded-xl overflow-hidden border border-white/10">
                      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/80 border-b border-white/8">
                        <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider">{lang}</span>
                        <CopyButton code={code} />
                      </div>
                      <SyntaxHighlighter
                        style={oneDark}
                        language={lang}
                        PreTag="div"
                        className="!m-0 !bg-zinc-950/80 text-xs"
                        {...props}
                      >
                        {code}
                      </SyntaxHighlighter>
                    </div>
                  );
                }
                return (
                  <code className="bg-zinc-900 border border-white/10 rounded px-1.5 py-0.5 text-xs font-mono text-indigo-300" {...props}>
                    {children}
                  </code>
                );
              },
              p: ({ children }) => <p className="mb-2 last:mb-0 text-sm leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 text-sm">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 text-sm">{children}</ol>,
              h1: ({ children }) => <h1 className="text-base font-bold mb-2 text-white">{children}</h1>,
              h2: ({ children }) => <h2 className="text-sm font-bold mb-2 text-zinc-100">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 text-zinc-200">{children}</h3>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-indigo-500 pl-3 my-2 text-zinc-400 italic">{children}</blockquote>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        ) : (
          <p className="text-sm leading-relaxed">{content}</p>
        )}

        {/* Streaming cursor */}
        {streaming && (
          <span className="inline-block w-2 h-4 bg-indigo-400 animate-pulse rounded-sm ml-0.5" />
        )}

        {/* Timestamp + Copy (for AI) */}
        {isAI && !streaming && (
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
            <span className="text-[10px] text-zinc-600">
              {timestamp ? new Date(timestamp).toLocaleTimeString() : ''}
            </span>
            <button
              onClick={copyAll}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Copy response"
            >
              {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function CopyButton({ code }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="text-xs text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
    >
      {copied ? <><Check size={11} className="text-green-400" /> Copied</> : <><Copy size={11} /> Copy</>}
    </button>
  );
}
