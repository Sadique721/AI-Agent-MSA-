import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Play, Copy, Download, X, FileCode } from 'lucide-react';
import { getMSAClient } from '../../core/apiClient';

const LANGUAGES = ['python', 'java', 'javascript', 'typescript', 'sql', 'bash', 'go', 'rust', 'cpp'];

export function CodeEditor({ onClose }) {
  const [code, setCode] = useState('// Write or paste your code here...\n');
  const [lang, setLang] = useState('python');

  const explainCode = () => {
    const prompt = `Explain this ${lang} code step by step:\n\`\`\`${lang}\n${code}\n\`\`\``;
    getMSAClient().sendCommand(prompt);
  };

  const debugCode = () => {
    const prompt = `Debug and fix this ${lang} code, explain what was wrong:\n\`\`\`${lang}\n${code}\n\`\`\``;
    getMSAClient().sendCommand(prompt);
  };

  const copyCode = () => navigator.clipboard.writeText(code);

  const downloadCode = () => {
    const ext = { python: 'py', java: 'java', javascript: 'js', typescript: 'ts', sql: 'sql', bash: 'sh', go: 'go', rust: 'rs', cpp: 'cpp' };
    const blob = new Blob([code], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `msa_code.${ext[lang] || 'txt'}`;
    a.click();
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 rounded-2xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900 border-b border-white/8">
        <div className="flex items-center gap-2">
          <FileCode size={14} className="text-indigo-400" />
          <span className="text-xs font-semibold text-zinc-300">Code Editor</span>
          <select
            value={lang}
            onChange={e => setLang(e.target.value)}
            className="bg-zinc-800 text-xs text-zinc-300 border border-white/10 rounded-lg px-2 py-0.5 outline-none ml-2"
          >
            {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={explainCode} className="text-[11px] px-2.5 py-1 bg-indigo-600/80 hover:bg-indigo-600 text-white rounded-lg transition-colors flex items-center gap-1">
            <Play size={10} /> Explain
          </button>
          <button onClick={debugCode} className="text-[11px] px-2.5 py-1 bg-amber-600/80 hover:bg-amber-600 text-white rounded-lg transition-colors flex items-center gap-1">
            <Play size={10} /> Debug
          </button>
          <button onClick={copyCode} className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors">
            <Copy size={12} />
          </button>
          <button onClick={downloadCode} className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors">
            <Download size={12} />
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors ml-1">
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={lang}
          value={code}
          onChange={val => setCode(val || '')}
          theme="vs-dark"
          options={{
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            wordWrap: 'on',
            padding: { top: 12, bottom: 12 },
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            renderLineHighlight: 'gutter',
            bracketPairColorization: { enabled: true },
            suggest: { showSnippets: true },
          }}
        />
      </div>
    </div>
  );
}
