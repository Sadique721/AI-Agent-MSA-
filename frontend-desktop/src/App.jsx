/**
 * App.jsx — MSA AI IDE
 * =====================
 * Full IDE layout: VS Code / Cursor / Antigravity style
 *
 * Layout:
 *   [Activity Bar] | [Sidebar] | [Editor + Tabs] | [AI Chat Panel]
 *                                [Terminal Panel]
 *                              [Status Bar]
 *
 * Features:
 *   • File Explorer with real filesystem tree (via backend /api/files)
 *   • Monaco Code Editor with syntax highlighting
 *   • Multi-tab file management
 *   • AI Chat panel with full attachment support (images, pdf, zip, doc…)
 *   • 8-agent switcher (MSA, Dev, Arch, Dr, Prof, Scribe, DevOps, SecOps)
 *   • Integrated terminal
 *   • Career OS Dashboard
 *   • Command Palette (Ctrl+K)
 *   • Status bar with Ollama model status
 */

import React, {
  useCallback, useEffect, useRef, useState, useMemo,
} from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Files, Search, GitBranch, Settings, Briefcase, Code2, Terminal,
  ChevronRight, ChevronDown, X, Plus, Minus, Copy, Check, Send,
  Paperclip, Command, Brain, Globe, Database, Zap, Cpu, User,
  Layers, Lock, Server, Pen, GraduationCap, FlaskConical,
  RefreshCw, BarChart3, Users, Target, TrendingUp, Clock, Mail,
  AlertCircle, FileText, Image as ImageIcon, Archive, File,
  FolderOpen, Folder, Maximize2, Minimize2, Circle, Activity,
  ChevronLeft, PanelBottom, PanelRight, Eye, Sparkles, Bot,
  Code, LayoutGrid, MessageSquare,
} from 'lucide-react';

import { useStore }   from './core/stateStore';
import { getMSAClient } from './core/apiClient';
import { SpatialCanvas } from './components/ui/SpatialCanvas';
import { ChatCard }      from './components/ui/ChatCard';

// ── API Base URLs ───────────────────────────────────────────────────────────────
// In Docker: nginx proxies /socket.io/ and /api/ to container ports internally.
// For local dev: reads from VITE env vars or falls back to localhost.
const API = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const FASTAPI = import.meta.env.VITE_FASTAPI_URL || 'http://localhost:8000';

// ─── Agent definitions ────────────────────────────────────────────────────────
const AGENTS = [
  { id: 'msa',    full: 'MSA Agent',     icon: Cpu,           bg: 'from-indigo-600 to-violet-700',   color: '#6366f1', desc: 'General AI OS' },
  { id: 'dev',    full: 'Dev Agent',     icon: Code2,         bg: 'from-emerald-500 to-green-700',   color: '#22c55e', desc: 'Software dev & code' },
  { id: 'arch',   full: 'Architect',     icon: Layers,        bg: 'from-orange-500 to-amber-600',    color: '#f97316', desc: 'System design' },
  { id: 'dr',     full: 'Research Dr',   icon: FlaskConical,  bg: 'from-purple-500 to-violet-700',   color: '#a855f7', desc: 'Research & analysis' },
  { id: 'prof',   full: 'Professor',     icon: GraduationCap, bg: 'from-pink-500 to-rose-600',       color: '#ec4899', desc: 'Teaching' },
  { id: 'scribe', full: 'Scribe',        icon: Pen,           bg: 'from-teal-500 to-cyan-600',       color: '#14b8a6', desc: 'Writing & docs' },
  { id: 'devops', full: 'DevOps',        icon: Server,        bg: 'from-amber-500 to-yellow-600',    color: '#f59e0b', desc: 'CI/CD & infra' },
  { id: 'secops', full: 'SecOps',        icon: Lock,          bg: 'from-red-500 to-rose-700',        color: '#ef4444', desc: 'Security' },
];

// ─── File type → icon + color ─────────────────────────────────────────────────
const EXT_MAP = {
  js: { color: '#f7df1e', label: 'JS' }, jsx: { color: '#61dafb', label: 'JSX' },
  ts: { color: '#3178c6', label: 'TS' }, tsx: { color: '#3178c6', label: 'TSX' },
  py: { color: '#3572A5', label: 'PY' }, json: { color: '#cbcb41', label: 'JSON' },
  css: { color: '#563d7c', label: 'CSS' }, html: { color: '#e34c26', label: 'HTML' },
  md: { color: '#83a598', label: 'MD' }, txt: { color: '#9e9e9e', label: 'TXT' },
  yml: { color: '#cb171e', label: 'YML' }, yaml: { color: '#cb171e', label: 'YML' },
  sh: { color: '#89e051', label: 'SH' }, bat: { color: '#89e051', label: 'BAT' },
  sql: { color: '#e38c00', label: 'SQL' }, png: { color: '#4caf50', label: 'IMG' },
  jpg: { color: '#4caf50', label: 'IMG' }, jpeg: { color: '#4caf50', label: 'IMG' },
  gif: { color: '#4caf50', label: 'IMG' }, svg: { color: '#4caf50', label: 'SVG' },
  pdf: { color: '#f44336', label: 'PDF' }, zip: { color: '#ff9800', label: 'ZIP' },
  doc: { color: '#2196f3', label: 'DOC' }, docx: { color: '#2196f3', label: 'DOC' },
  xlsx: { color: '#4caf50', label: 'XLS' }, csv: { color: '#4caf50', label: 'CSV' },
};

function getExt(name = '') { return name.split('.').pop().toLowerCase(); }
function getExtInfo(name) {
  const ext = getExt(name);
  return EXT_MAP[ext] || { color: '#71717a', label: ext.toUpperCase().slice(0, 3) || 'FILE' };
}

// ─── Utility: copy button ─────────────────────────────────────────────────────
function CopyBtn({ text }) {
  const [c, setC] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setC(true); setTimeout(() => setC(false), 2000); }}
      className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1 text-[10px]">
      {c ? <><Check size={11} className="text-green-400" /> Copied</> : <><Copy size={11} /> Copy</>}
    </button>
  );
}

// ─── File attachment preview ──────────────────────────────────────────────────
function AttachmentChip({ file, onRemove }) {
  const ext = getExt(file.name);
  const info = getExtInfo(file.name);
  const isImage = ['png','jpg','jpeg','gif','webp','svg'].includes(ext);
  const preview = isImage ? URL.createObjectURL(file) : null;

  return (
    <div className="flex items-center gap-1.5 bg-zinc-800 border border-white/10 rounded-lg px-2 py-1 group">
      {isImage
        ? <img src={preview} alt={file.name} className="w-5 h-5 rounded object-cover" />
        : <span className="text-[9px] font-bold px-1 py-0.5 rounded" style={{ backgroundColor: info.color + '33', color: info.color }}>{info.label}</span>
      }
      <span className="text-[11px] text-zinc-300 max-w-[100px] truncate">{file.name}</span>
      <span className="text-[9px] text-zinc-600">{(file.size / 1024).toFixed(1)}KB</span>
      <button onClick={onRemove} className="text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all ml-0.5">
        <X size={11} />
      </button>
    </div>
  );
}

// ─── Chat Bubble ──────────────────────────────────────────────────────────────
function ChatBubble({ message, agentId }) {
  const { role, content, streaming, timestamp, attachments } = message;
  const isAI = role === 'assistant';
  const agent = AGENTS.find(a => a.id === agentId) || AGENTS[0];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className={`flex gap-2.5 group ${isAI ? 'flex-row' : 'flex-row-reverse'} mb-4`}>
      <div className={`w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5 bg-gradient-to-br ${
        isAI ? agent.bg : 'from-zinc-700 to-zinc-800 border border-white/10'}`}>
        {isAI ? <agent.icon size={13} className="text-white" /> : <User size={13} className="text-zinc-300" />}
      </div>
      <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 ${
        isAI ? 'bg-zinc-900 border border-white/8 text-zinc-100'
             : 'bg-gradient-to-br from-indigo-600/90 to-violet-700/80 text-white border border-indigo-500/30'}`}>
        {attachments?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {attachments.map((f, i) => {
              const ext = getExt(f.name);
              const isImg = ['png','jpg','jpeg','gif','webp'].includes(ext);
              return isImg
                ? <img key={i} src={f.data} alt={f.name} className="max-w-[200px] max-h-[140px] rounded-lg object-cover border border-white/10" />
                : <div key={i} className="flex items-center gap-1.5 bg-white/8 rounded-lg px-2 py-1 text-[11px]">
                    <span style={{ color: getExtInfo(f.name).color }}>{getExtInfo(f.name).label}</span>
                    <span className="text-zinc-300">{f.name}</span>
                  </div>;
            })}
          </div>
        )}
        {isAI ? (
          <ReactMarkdown className="prose prose-invert prose-xs max-w-none leading-relaxed"
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const lang = match?.[1] || '';
                const code = String(children).replace(/\n$/, '');
                if (!inline && lang) return (
                  <div className="my-2 rounded-lg overflow-hidden border border-white/10">
                    <div className="flex items-center justify-between px-3 py-1.5 bg-black/40 border-b border-white/8">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase">{lang}</span>
                      <CopyBtn text={code} />
                    </div>
                    <SyntaxHighlighter style={oneDark} language={lang} PreTag="div" className="!m-0 !bg-zinc-950 !text-xs" {...props}>{code}</SyntaxHighlighter>
                  </div>
                );
                return <code className="bg-zinc-800 border border-white/10 rounded px-1.5 py-0.5 text-[11px] font-mono text-indigo-300" {...props}>{children}</code>;
              },
              p: ({ children }) => <p className="mb-1.5 last:mb-0 text-[13px] leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-1.5 space-y-0.5 text-[13px]">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-1.5 space-y-0.5 text-[13px]">{children}</ol>,
              h1: ({ children }) => <h1 className="text-sm font-bold mb-1.5 text-white">{children}</h1>,
              h2: ({ children }) => <h2 className="text-[13px] font-bold mb-1 text-zinc-100">{children}</h2>,
              blockquote: ({ children }) => <blockquote className="border-l-2 border-indigo-500 pl-2.5 my-1.5 text-zinc-400 italic text-[13px]">{children}</blockquote>,
            }}>{content}</ReactMarkdown>
        ) : <p className="text-[13px] leading-relaxed">{content}</p>}
        {streaming && <span className="inline-block w-2 h-3.5 bg-indigo-400 animate-pulse rounded-sm ml-0.5 align-middle" />}
        {isAI && !streaming && (
          <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-white/5">
            <span className="text-[10px] text-zinc-700">{timestamp ? new Date(timestamp).toLocaleTimeString() : ''}</span>
            <CopyBtn text={content} />
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Thinking Indicator ───────────────────────────────────────────────────────
const STATUS_INFO = {
  thinking: { label: 'Thinking…', color: 'text-violet-400', dot: 'bg-violet-400' },
  searching: { label: 'Searching web…', color: 'text-cyan-400', dot: 'bg-cyan-400' },
  coding: { label: 'Writing code…', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  analyzing: { label: 'Analyzing…', color: 'text-amber-400', dot: 'bg-amber-400' },
};
function ThinkingDots({ status }) {
  const s = STATUS_INFO[status]; if (!s) return null;
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-white/8 rounded-xl mb-3 w-fit">
      {[0,1,2].map(i => (
        <motion.div key={i} className={`w-1.5 h-1.5 rounded-full ${s.dot}`}
          animate={{ opacity: [0.3,1,0.3], scale: [0.8,1.2,0.8] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }} />
      ))}
      <span className={`text-xs font-medium ${s.color}`}>{s.label}</span>
    </motion.div>
  );
}

// ─── File Tree Node ───────────────────────────────────────────────────────────
function FileNode({ node, depth = 0, onOpen }) {
  const [open, setOpen] = useState(depth < 1);
  const isDir = node.type === 'dir';
  const info  = isDir ? null : getExtInfo(node.name);
  const pad   = depth * 12 + 8;

  return (
    <div>
      <div
        onClick={() => isDir ? setOpen(p => !p) : onOpen(node)}
        className="flex items-center gap-1.5 py-[3px] pr-2 rounded cursor-pointer hover:bg-white/5 group transition-colors select-none"
        style={{ paddingLeft: pad }}>
        {isDir
          ? (open ? <ChevronDown size={11} className="text-zinc-500 flex-shrink-0" /> : <ChevronRight size={11} className="text-zinc-500 flex-shrink-0" />)
          : <span className="w-3 flex-shrink-0" />}
        {isDir
          ? (open ? <FolderOpen size={13} className="text-amber-400 flex-shrink-0" /> : <Folder size={13} className="text-amber-500 flex-shrink-0" />)
          : <span className="text-[9px] font-bold w-5 flex-shrink-0 text-center" style={{ color: info.color }}>{info.label}</span>}
        <span className={`text-[12px] truncate ${isDir ? 'text-zinc-300' : 'text-zinc-400 group-hover:text-zinc-200'}`}>{node.name}</span>
      </div>
      <AnimatePresence>
        {isDir && open && node.children && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }}>
            {node.children.map((c, i) => <FileNode key={i} node={c} depth={depth + 1} onOpen={onOpen} />)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── File Explorer Sidebar ────────────────────────────────────────────────────
function FileExplorer({ onOpenFile }) {
  const [tree, setTree]     = useState(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch]  = useState('');
  const [root, setRoot]      = useState('D:\\My Self Details\\Programs\\AI\\msa_agent');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/files/tree?path=${encodeURIComponent(root)}&depth=4`);
      if (r.ok) setTree(await r.json());
    } catch (_) {}
    setLoading(false);
  }, [root]);

  useEffect(() => { load(); }, [load]);

  const flat = useMemo(() => {
    if (!search || !tree) return null;
    const results = [];
    const walk = (nodes) => nodes.forEach(n => {
      if (n.type === 'file' && n.name.toLowerCase().includes(search.toLowerCase())) results.push(n);
      if (n.children) walk(n.children);
    });
    if (tree.children) walk(tree.children);
    return results;
  }, [search, tree]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 flex-shrink-0">
        <span className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Explorer</span>
        <div className="flex items-center gap-1">
          <button onClick={load} className={`p-1 hover:bg-white/8 rounded text-zinc-600 hover:text-white ${loading ? 'animate-spin' : ''}`}>
            <RefreshCw size={11} />
          </button>
          <button onClick={() => onOpenFile && onOpenFile({ type: 'new', name: 'Untitled' })}
            className="p-1 hover:bg-white/8 rounded text-zinc-600 hover:text-white">
            <Plus size={11} />
          </button>
        </div>
      </div>
      {/* Search */}
      <div className="px-2 py-1.5 border-b border-white/5 flex-shrink-0">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search files…"
          className="w-full bg-zinc-800/60 border border-white/8 rounded-lg px-2.5 py-1.5 text-[11px] text-zinc-300 placeholder-zinc-600 outline-none focus:border-indigo-500/40" />
      </div>
      {/* Tree or search results */}
      <div className="flex-1 overflow-y-auto py-1" style={{ scrollbarWidth: 'thin', scrollbarColor: '#3f3f46 transparent' }}>
        {loading && <div className="text-center text-zinc-700 text-[11px] py-8">Loading…</div>}
        {!loading && !tree && <div className="text-center text-zinc-700 text-[11px] py-8">Backend offline</div>}
        {!loading && tree && !flat && (
          <div>
            <div className="flex items-center gap-1.5 px-2 py-1.5">
              <ChevronDown size={11} className="text-zinc-500" />
              <FolderOpen size={13} className="text-amber-400" />
              <span className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wide">msa_agent</span>
            </div>
            {tree.children?.map((c, i) => <FileNode key={i} node={c} depth={1} onOpen={onOpenFile} />)}
          </div>
        )}
        {flat && (
          <div className="p-2 space-y-0.5">
            <div className="text-[10px] text-zinc-600 mb-2 px-1">{flat.length} results</div>
            {flat.map((f, i) => (
              <div key={i} onClick={() => onOpenFile(f)}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer">
                <span className="text-[9px] font-bold" style={{ color: getExtInfo(f.name).color }}>{getExtInfo(f.name).label}</span>
                <span className="text-[12px] text-zinc-400">{f.name}</span>
                <span className="text-[10px] text-zinc-600 ml-auto truncate max-w-[80px]">{f.path?.split('\\').slice(-2, -1)[0]}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Career Dashboard ─────────────────────────────────────────────────────────
const STATUS_BADGE = {
  applied: 'text-blue-300 bg-blue-600/20', interview: 'text-emerald-300 bg-emerald-600/20',
  offered: 'text-violet-300 bg-violet-600/20', rejected: 'text-red-300 bg-red-600/20',
  discovered: 'text-zinc-400 bg-zinc-700/40', queued: 'text-yellow-300 bg-yellow-600/20',
};
function CareerDashboard() {
  const [stats, setStats] = useState({});
  const [jobs, setJobs]   = useState([]);
  const [tab, setTab]     = useState('funnel');
  const [loading, setL]   = useState(false);

  const load = useCallback(async () => {
    setL(true);
    try {
      const a = await fetch(`${API}/api/career/analytics`).then(r => r.ok ? r.json() : {});
      setStats(a);
      const j = await fetch(`${API}/api/career/applications`).then(r => r.ok ? r.json() : []);
      setJobs(Array.isArray(j) ? j.slice(0, 25) : []);
    } catch (_) {}
    setL(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const funnel = stats.funnel || {};
  const maxF   = Math.max(...Object.values(funnel), 1);
  const COLORS  = { discovered:'bg-zinc-500', queued:'bg-yellow-500', applied:'bg-blue-500', interview:'bg-emerald-500', offered:'bg-violet-500', rejected:'bg-red-500' };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/8 flex-shrink-0">
        <span className="text-xs font-bold text-white flex items-center gap-2"><Briefcase size={13} className="text-indigo-400" /> Career OS</span>
        <button onClick={load} className={`p-1 rounded text-zinc-500 hover:text-white ${loading ? 'animate-spin' : ''}`}><RefreshCw size={12} /></button>
      </div>
      {/* Stats */}
      <div className="grid grid-cols-4 gap-2 px-3 py-2.5 flex-shrink-0">
        {[['Applied',funnel.applied||0,'text-blue-400'],['Interview',funnel.interview||0,'text-emerald-400'],['Offered',funnel.offered||0,'text-violet-400'],['Rate',`${Math.round((stats.response_rate||0)*100)}%`,'text-amber-400']].map(([l,v,c]) => (
          <div key={l} className="bg-white/4 border border-white/8 rounded-xl p-2.5">
            <div className={`text-[10px] uppercase font-bold ${c} mb-1`}>{l}</div>
            <div className="text-lg font-extrabold text-white">{v}</div>
          </div>
        ))}
      </div>
      {/* Tabs */}
      <div className="flex gap-1 px-3 pb-2 flex-shrink-0">
        {[['funnel','Funnel',BarChart3],['pipeline','Jobs',Briefcase],['crm','Contacts',Users]].map(([id,label,Icon]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${tab===id?'bg-indigo-600/25 text-white border border-indigo-500/30':'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}`}>
            <Icon size={11} />{label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
        {tab === 'funnel' && Object.entries(funnel).map(([stage, count]) => (
          <div key={stage} className="flex items-center gap-2">
            <div className="w-16 text-[10px] text-zinc-500 capitalize text-right flex-shrink-0">{stage}</div>
            <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
              <motion.div initial={{ width: 0 }} animate={{ width: `${(count/maxF)*100}%` }}
                className={`h-1.5 rounded-full ${COLORS[stage]||'bg-zinc-500'}`} />
            </div>
            <div className="w-6 text-[10px] text-zinc-500 font-mono">{count}</div>
          </div>
        ))}
        {tab === 'pipeline' && jobs.map((j, i) => (
          <div key={i} className="bg-white/3 border border-white/8 rounded-xl p-2.5 flex items-center justify-between hover:bg-white/5 transition-all">
            <div>
              <div className="text-[12px] font-semibold text-zinc-200">{j.title||j.job_id}</div>
              <div className="text-[10px] text-zinc-500">{j.company}</div>
            </div>
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${STATUS_BADGE[j.status]||'text-zinc-400 bg-zinc-700/30'}`}>{j.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Command Palette ──────────────────────────────────────────────────────────
// Unified — all handled by ALL agents + ALL models together
const QUICK_ACTIONS = [
  { icon: Zap,          label: 'Write a FastAPI endpoint with authentication',   cmd: 'Write a complete FastAPI endpoint with JWT authentication, including routes, middleware, and error handling.' },
  { icon: Brain,        label: 'Explain how RAG systems work',                   cmd: 'Explain in detail how RAG (Retrieval Augmented Generation) systems work, with architecture and code examples.' },
  { icon: AlertCircle,  label: 'Debug my Python traceback error',                cmd: 'Help me debug this Python traceback error — analyze the cause and provide a fix: ' },
  { icon: BarChart3,    label: 'Create a data analysis script with pandas',      cmd: 'Create a complete Python data analysis script using pandas including data loading, cleaning, analysis, and visualization.' },
  { icon: Layers,       label: 'Design a microservices architecture',            cmd: 'Design a production-grade microservices architecture including API gateway, service discovery, and inter-service communication.' },
  { icon: Lock,         label: 'Review my code for security vulnerabilities',    cmd: 'Review this code for OWASP security vulnerabilities, injection risks, and auth issues. Provide a fix for each: ' },
  { icon: Globe,        label: 'Search web & research',                          cmd: 'Search the web and research: ' },
  { icon: Database,     label: 'Recall from memory',                             cmd: 'What do you remember about: ' },
  { icon: Code2,        label: 'Generate any code or script',                   cmd: 'Write clean, production-ready code for: ' },
  { icon: Briefcase,    label: 'Discover & apply to jobs',                      cmd: 'Discover relevant job listings for a Software Engineer and create an application strategy.' },
  { icon: Pen,          label: 'Write a professional document',                  cmd: 'Write a professional document / cover letter / report for: ' },
  { icon: Files,        label: 'Analyze an uploaded file',                       cmd: 'Analyze the attached file and give a detailed breakdown of its contents, structure, and key insights.' },
  { icon: FlaskConical, label: 'Deep research on any topic',                    cmd: 'Conduct deep research and provide a comprehensive summary with citations on: ' },
  { icon: Server,       label: 'DevOps: CI/CD pipeline setup',                  cmd: 'Set up a complete CI/CD pipeline with GitHub Actions / Docker / Kubernetes for: ' },
  { icon: GraduationCap,label: 'Teach me step-by-step',                        cmd: 'Teach me step-by-step with examples: ' },
  { icon: Target,       label: 'Optimize & improve performance',                 cmd: 'Analyze and optimize this for better performance, scalability, and clean architecture: ' },
];

function CmdPalette({ open, onClose, onSubmit }) {
  const [q, setQ] = useState('');
  const ref = useRef(null);
  useEffect(() => { if (open) { setQ(''); setTimeout(() => ref.current?.focus(), 50); }}, [open]);
  const filtered = QUICK_ACTIONS.filter(a => a.label.toLowerCase().includes(q.toLowerCase()));
  const pick = cmd => { onSubmit(cmd); onClose(); setQ(''); };
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50" onClick={onClose} />
          <motion.div initial={{opacity:0,scale:0.94,y:-16}} animate={{opacity:1,scale:1,y:0}}
            exit={{opacity:0,scale:0.94}} transition={{duration:.16,ease:'easeOut'}}
            className="fixed top-[16%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 px-4">
            <div className="bg-zinc-900/98 border border-white/15 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-2xl">
              <div className="flex items-center gap-3 px-5 py-3.5 border-b border-white/10">
                <Command size={15} className="text-zinc-500" />
                <input ref={ref} value={q} onChange={e=>setQ(e.target.value)}
                  onKeyDown={e=>{if(e.key==='Escape')onClose();if(e.key==='Enter'&&q.trim())pick(q);}}
                  placeholder="Ask MSA IDE anything, or pick an action…"
                  className="flex-1 bg-transparent text-[13px] text-white placeholder-zinc-600 outline-none" />
                <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">ESC</kbd>
              </div>
              <div className="p-2 max-h-80 overflow-y-auto">
                <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold px-2 mb-2">Quick Actions</div>
                {filtered.map((a,i)=>(
                  <button key={i} onClick={()=>pick(a.cmd)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-white/6 transition-colors group">
                    <div className="w-7 h-7 rounded-lg bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center group-hover:bg-indigo-600/25 transition-colors">
                      <a.icon size={13} className="text-indigo-400" />
                    </div>
                    <span className="text-[13px] text-zinc-300 group-hover:text-white">{a.label}</span>
                    <ChevronRight size={11} className="text-zinc-700 ml-auto" />
                  </button>
                ))}
                {q && (
                  <button onClick={()=>pick(q)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left hover:bg-indigo-600/10 border border-indigo-500/15 transition-colors mt-1.5">
                    <div className="w-7 h-7 rounded-lg bg-indigo-600/25 flex items-center justify-center">
                      <Send size={12} className="text-indigo-400" />
                    </div>
                    <span className="text-[13px] text-indigo-300">Send: <em className="not-italic font-semibold text-white">"{q}"</em></span>
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

// ─── Composer (Chat Input + File Upload) ──────────────────────────────────────
function Composer({ onSend, onOpenPalette, agentId, disabled }) {
  const [text, setText]   = useState('');
  const [files, setFiles] = useState([]);
  const fileRef           = useRef(null);
  const agent             = AGENTS.find(a => a.id === agentId) || AGENTS[0];

  const readFile = file => new Promise(res => {
    const ext = getExt(file.name);
    const isImg = ['png','jpg','jpeg','gif','webp','svg'].includes(ext);
    if (isImg) {
      const reader = new FileReader();
      reader.onload = e => res({ name: file.name, size: file.size, type: 'image', data: e.target.result });
      reader.readAsDataURL(file);
    } else {
      const reader = new FileReader();
      reader.onload = e => res({ name: file.name, size: file.size, type: 'text', data: e.target.result });
      reader.readAsText(file);
    }
  });

  const addFiles = async picked => {
    const arr = Array.from(picked);
    const read = await Promise.all(arr.map(readFile));
    setFiles(p => [...p, ...read]);
  };

  const send = () => {
    if (!text.trim() && files.length === 0) return;
    if (disabled) return;
    onSend(text, files);
    setText(''); setFiles([]);
  };

  const handleKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }};

  const handleDrop = e => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  };

  return (
    <div className="border-t border-white/8 bg-[#0d0d14] flex-shrink-0 px-3 pb-3 pt-2"
      onDrop={handleDrop} onDragOver={e => e.preventDefault()}>
      {/* Attachment chips */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2 px-1">
          {files.map((f, i) => (
            <AttachmentChip key={i} file={f} onRemove={() => setFiles(p => p.filter((_, j) => j !== i))} />
          ))}
        </div>
      )}
      {/* Input box */}
      <div className="flex items-end gap-2 bg-zinc-900/80 border border-white/10 rounded-xl p-2.5 focus-within:border-indigo-500/40 transition-all">
        <div className="w-6 h-6 rounded-lg flex-shrink-0 flex items-center justify-center bg-gradient-to-br from-indigo-600 to-violet-700 mb-0.5">
          <Sparkles size={12} className="text-white" />
        </div>
        <textarea rows={1} value={text} onChange={e => setText(e.target.value)} onKeyDown={handleKey}
          placeholder="Ask anything — code, debug, research, design, security, writing… (drag files here or 📎)"
          className="flex-1 bg-transparent text-[13px] text-white placeholder-zinc-600 outline-none resize-none leading-relaxed max-h-28 overflow-y-auto"
          style={{ scrollbarWidth: 'none' }} />
        <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
          <button onClick={() => fileRef.current?.click()} title="Attach file"
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/8 transition-all">
            <Paperclip size={14} />
          </button>
          <button onClick={onOpenPalette} title="Command palette (Ctrl+K)"
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/8 transition-all">
            <Command size={14} />
          </button>
          <motion.button onClick={send} disabled={(!text.trim() && files.length === 0) || disabled}
            whileHover={{scale:1.05}} whileTap={{scale:0.93}}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-bold flex items-center gap-1.5 transition-all ${
              (text.trim() || files.length > 0) && !disabled
                ? `bg-gradient-to-r ${agent.bg} text-white shadow-md`
                : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'}`}>
            <Send size={11} /> Send
          </motion.button>
        </div>
      </div>
      <input ref={fileRef} type="file" multiple className="hidden"
        accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.zip,.txt,.md,.json,.py,.js,.ts,.jsx,.tsx,.html,.css,.sql,.sh,.bat,.yml,.yaml"
        onChange={e => addFiles(e.target.files)} />
      <div className="text-[10px] text-zinc-700 text-center mt-1.5">
        Enter to send · Shift+Enter new line · Ctrl+K commands · Drag &amp; drop files
      </div>
    </div>
  );
}

// ─── Tab Bar ──────────────────────────────────────────────────────────────────
function TabBar({ tabs, active, onSelect, onClose }) {
  return (
    <div className="flex items-center bg-[#0e0e17] border-b border-white/8 overflow-x-auto flex-shrink-0" style={{ scrollbarWidth: 'none' }}>
      {tabs.map(tab => {
        const isActive = tab.id === active;
        const info = tab.type !== 'welcome' ? getExtInfo(tab.name) : { color: '#6366f1', label: '★' };
        return (
          <div key={tab.id}
            className={`flex items-center gap-2 px-3 py-2 border-r border-white/6 cursor-pointer min-w-[120px] max-w-[180px] flex-shrink-0 group transition-all ${
              isActive ? 'bg-[#13131f] border-t-2 border-t-indigo-500' : 'hover:bg-white/4'}`}
            onClick={() => onSelect(tab.id)}>
            <span className="text-[9px] font-bold flex-shrink-0" style={{ color: info.color }}>{info.label}</span>
            <span className={`text-[11px] truncate flex-1 ${isActive ? 'text-white' : 'text-zinc-400'}`}>{tab.name}</span>
            {tab.modified && <Circle size={6} className="text-indigo-400 flex-shrink-0" />}
            <button onClick={e => { e.stopPropagation(); onClose(tab.id); }}
              className="text-zinc-700 hover:text-zinc-300 opacity-0 group-hover:opacity-100 flex-shrink-0 transition-all">
              <X size={11} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ─── Welcome Screen (Unified — ALL agents + ALL models work on EVERY task) ─────
const UNIFIED_PROMPTS = [
  { icon: Zap,          color: '#f59e0b', label: 'Write a FastAPI endpoint with authentication',   cmd: 'Write a complete FastAPI endpoint with JWT authentication.' },
  { icon: Brain,        color: '#8b5cf6', label: 'Explain how RAG systems work',                   cmd: 'Explain how RAG (Retrieval Augmented Generation) systems work with architecture diagrams and code.' },
  { icon: AlertCircle,  color: '#ef4444', label: 'Debug my Python traceback error',                cmd: 'Help me debug this Python traceback error: ' },
  { icon: BarChart3,    color: '#06b6d4', label: 'Create a data analysis script with pandas',      cmd: 'Create a complete Python data analysis script using pandas with cleaning, analysis, and charts.' },
  { icon: Layers,       color: '#f97316', label: 'Design a microservices architecture',            cmd: 'Design a production microservices architecture with API gateway and service discovery.' },
  { icon: Lock,         color: '#22c55e', label: 'Review my code for security vulnerabilities',    cmd: 'Review this code for OWASP security vulnerabilities and provide fixes: ' },
];

function WelcomeScreen({ onAction }) {
  const [inputVal, setInputVal] = useState('');
  const inputRef = useRef(null);
  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 300); }, []);

  const handleKey = e => { if (e.key === 'Enter' && inputVal.trim()) { onAction(inputVal); setInputVal(''); } };

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 select-none">
      {/* Logo + title */}
      <motion.div initial={{scale:0.7,opacity:0}} animate={{scale:1,opacity:1}} transition={{duration:0.5,ease:'backOut'}}
        className="relative mb-5">
        {/* Ring of agent icons */}
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 flex items-center justify-center shadow-2xl shadow-indigo-900/50">
          <Sparkles size={32} className="text-white" />
        </div>
        {/* Orbiting mini agent dots */}
        {AGENTS.slice(0,6).map((ag, i) => {
          const angle = (i / 6) * 360 - 90;
          const rad = angle * Math.PI / 180;
          const r = 48;
          return (
            <motion.div key={ag.id}
              initial={{opacity:0,scale:0}} animate={{opacity:1,scale:1}} transition={{delay:0.3+i*0.06}}
              style={{ position:'absolute', left: 40 + r*Math.cos(rad) - 8, top: 40 + r*Math.sin(rad) - 8 }}
              className={`w-4 h-4 rounded-full bg-gradient-to-br ${ag.bg} border-2 border-[#0a0a0f] flex items-center justify-center`}
              title={ag.full}>
              <ag.icon size={7} className="text-white" />
            </motion.div>
          );
        })}
      </motion.div>

      <motion.h1 initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:0.15}}
        className="text-[22px] font-extrabold text-white mb-0.5 tracking-tight">MSA AI IDE</motion.h1>
      <motion.p initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.2}}
        className="text-[12px] text-zinc-500 mb-1">Anti-Gravity OS · All 8 Agents + 4 Models working as ONE</motion.p>

      {/* Unified agent badges */}
      <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.25}}
        className="flex flex-wrap gap-1.5 justify-center mb-6">
        {AGENTS.map(ag => (
          <div key={ag.id} className={`flex items-center gap-1 px-2 py-0.5 rounded-full border bg-gradient-to-r ${ag.bg} bg-opacity-10`}
            style={{ borderColor: ag.color + '40', backgroundColor: ag.color + '18' }}>
            <ag.icon size={9} style={{ color: ag.color }} />
            <span className="text-[9px] font-bold" style={{ color: ag.color }}>{ag.full}</span>
          </div>
        ))}
      </motion.div>

      {/* Big unified input */}
      <motion.div initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} transition={{delay:0.3}}
        className="w-full max-w-2xl mb-6">
        <div className="flex items-center gap-3 bg-white/4 border border-white/12 rounded-2xl px-4 py-3.5 focus-within:border-indigo-500/50 focus-within:bg-white/6 transition-all shadow-xl">
          <Sparkles size={16} className="text-indigo-400 flex-shrink-0" />
          <input ref={inputRef} value={inputVal} onChange={e => setInputVal(e.target.value)} onKeyDown={handleKey}
            placeholder="Ask anything — code, debug, research, design, write, analyze…"
            className="flex-1 bg-transparent text-[14px] text-white placeholder-zinc-600 outline-none" />
          <motion.button onClick={() => { if (inputVal.trim()) { onAction(inputVal); setInputVal(''); }}} whileHover={{scale:1.05}} whileTap={{scale:0.95}}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-[11px] font-bold text-white transition-colors">
            <Send size={11}/> Go
          </motion.button>
        </div>
        <p className="text-[10px] text-zinc-700 text-center mt-1.5">Enter to send · All agents collaborate automatically · Attach any file via 📎 in chat</p>
      </motion.div>

      {/* Unified prompt cards — all handled by ALL agents together */}
      <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.35}}
        className="grid grid-cols-3 gap-2 w-full max-w-2xl">
        {UNIFIED_PROMPTS.map((s, i) => (
          <motion.button key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:0.35+i*0.04}}
            onClick={() => onAction(s.cmd)} whileHover={{scale:1.02,y:-1}} whileTap={{scale:0.97}}
            className="flex items-start gap-2.5 p-3 bg-white/3 border border-white/7 rounded-xl text-left hover:bg-white/6 hover:border-white/15 transition-all group">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
              style={{ backgroundColor: s.color + '1a', border: `1px solid ${s.color}33` }}>
              <s.icon size={13} style={{ color: s.color }} />
            </div>
            <span className="text-[11px] text-zinc-500 group-hover:text-zinc-200 leading-relaxed">{s.label}</span>
          </motion.button>
        ))}
      </motion.div>

      {/* Model pills */}
      <motion.div initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.6}}
        className="flex items-center gap-2 mt-5">
        {[['qwen2.5:7b','#6366f1'],['deepseek-r1:7b','#a855f7'],['qwen2.5:0.5b','#22c55e'],['nomic-embed','#06b6d4']].map(([m,c]) => (
          <div key={m} className="flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-mono"
            style={{ borderColor: c+'33', color: c, backgroundColor: c+'10' }}>
            <Circle size={5} fill={c} stroke="none" />{m}
          </div>
        ))}
        <span className="text-[9px] text-zinc-700 ml-1">parallel routing</span>
      </motion.div>
    </div>
  );
}

// ─── Bottom Terminal Panel ────────────────────────────────────────────────────
function TerminalPanel({ onClose }) {
  const [lines, setLines] = useState(['MSA IDE Terminal — type commands below…']);
  const [input, setInput] = useState('');
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [lines]);

  const run = async () => {
    if (!input.trim()) return;
    const cmd = input.trim();
    setLines(p => [...p, `$ ${cmd}`]);
    setInput('');
    try {
      const r = await fetch(`${API}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-MSA-Key': 'MSA_SECURE_123' },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await r.json();
      setLines(p => [...p, data.response || data.output || '(no output)']);
    } catch (e) {
      setLines(p => [...p, `Error: ${e.message}`]);
    }
  };

  return (
    <div className="flex flex-col bg-[#0a0a0f] border-t border-white/8" style={{ height: 200 }}>
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-white/6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wider font-bold text-zinc-500">Terminal</span>
          <div className="flex gap-1">
            {['PROBLEMS','OUTPUT','TERMINAL'].map(l => (
              <button key={l} className="text-[10px] text-zinc-600 hover:text-zinc-400 px-2 py-0.5 rounded hover:bg-white/5 transition-all">{l}</button>
            ))}
          </div>
        </div>
        <button onClick={onClose} className="text-zinc-600 hover:text-zinc-300 transition-colors"><X size={13} /></button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 font-mono text-[11px] text-emerald-400 space-y-0.5" style={{ scrollbarWidth: 'thin' }}>
        {lines.map((l, i) => (
          <div key={i} className={l.startsWith('$') ? 'text-white' : 'text-emerald-400'}>{l}</div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="flex items-center gap-2 px-4 py-2 border-t border-white/6 flex-shrink-0">
        <span className="text-emerald-500 font-mono text-[11px]">❯</span>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
          placeholder="run command…"
          className="flex-1 bg-transparent text-[11px] font-mono text-white outline-none placeholder-zinc-700" />
      </div>
    </div>
  );
}

// ─── Status Bar ───────────────────────────────────────────────────────────────
function StatusBar({ agentId, thinkingStatus, modelStatus }) {
  const agent = AGENTS.find(a => a.id === agentId) || AGENTS[0];
  return (
    <div className="flex items-center justify-between px-3 py-[3px] bg-indigo-900/40 border-t border-indigo-700/30 flex-shrink-0 text-[10px]">
      <div className="flex items-center gap-3 text-indigo-300/70">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: agent.color }} />
          <span className="font-medium">{agent.full}</span>
        </div>
        {thinkingStatus && <span className="italic text-indigo-300/50">{thinkingStatus}</span>}
      </div>
      <div className="flex items-center gap-3 text-indigo-300/50">
        <span className={modelStatus?.ollama_running ? 'text-emerald-400' : 'text-red-400'}>
          {modelStatus?.ollama_running ? '● Ollama online' : '○ Ollama offline'}
        </span>
        {modelStatus?.ollama_running && <span>qwen2.5:7b · deepseek-r1 · nomic</span>}
        <span>localhost:5000</span>
        <span>V6.0</span>
        <span>UTF-8</span>
      </div>
    </div>
  );
}

// ─── Activity Bar ─────────────────────────────────────────────────────────────
const ACTIVITIES = [
  { id: 'explorer', icon: Files,      title: 'Explorer' },
  { id: 'search',   icon: Search,     title: 'Search' },
  { id: 'git',      icon: GitBranch,  title: 'Source Control' },
  { id: 'agents',   icon: Bot,        title: 'Agents' },
  { id: 'career',   icon: Briefcase,  title: 'Career OS' },
  { id: 'settings', icon: Settings,   title: 'Settings' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════════════════
export default function App() {
  const { conversations, addCard, addStreamToken, startStreamMessage, finalizeStreamMessage, setAgentStatus } = useStore();

  // Layout state
  const [activity,        setActivity]        = useState('explorer');
  const [sidebarOpen,     setSidebarOpen]      = useState(true);
  const [chatOpen,        setChatOpen]         = useState(true);
  const [terminalOpen,    setTerminalOpen]     = useState(false);
  const [cmdOpen,         setCmdOpen]          = useState(false);

  // IDE tabs
  const [tabs,     setTabs]    = useState([{ id: 'welcome', name: 'Welcome', type: 'welcome' }]);
  const [activeTab, setActiveTab] = useState('welcome');

  // Agent & model
  const [activeAgent,  setActiveAgent]  = useState('msa');
  const [thinkingStatus, setThinking]  = useState('');
  const [modelStatus,  setModelStatus] = useState(null);

  const chatEndRef = useRef(null);

  // ── SocketIO + keys ──────────────────────────────────────────────────────
  useEffect(() => {
    const client = getMSAClient();
    client.onToken(data => { const t = typeof data === 'string' ? data : data.token || ''; if (t) addStreamToken(t); });
    client.onStatus(data => {
      const txt = (data.message || '').toLowerCase();
      setThinking(txt.includes('search') ? 'searching' : txt.includes('code') ? 'coding' : txt ? 'thinking' : '');
    });
    client.onMessage(data => {
      if (data.agent_event) return;
      const t = data.response || data.content || '';
      if (t) { finalizeStreamMessage(t); setThinking(''); }
    });
    client.connect();

    const onKey = e => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === '`') { e.preventDefault(); setTerminalOpen(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); setSidebarOpen(p => !p); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [addStreamToken, finalizeStreamMessage]);

  // ── Model status polling ──────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try { const r = await fetch(`${API}/api/models`); if (r.ok) setModelStatus(await r.json()); } catch (_) {}
    };
    poll(); const t = setInterval(poll, 30000); return () => clearInterval(t);
  }, []);

  // ── Auto-scroll chat ──────────────────────────────────────────────────────
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [conversations, thinkingStatus]);

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = useCallback((text, files = []) => {
    const content = text.trim() || (files.length > 0 ? `[${files.length} file(s) attached]` : '');
    if (!content && files.length === 0) return;
    addCard({ role: 'user', content, attachments: files });
    startStreamMessage();
    setThinking('thinking');
    // Include file text in the prompt sent to AI
    let prompt = text;
    files.forEach(f => {
      if (f.type === 'text') prompt += `\n\n--- File: ${f.name} ---\n${f.data?.slice(0, 8000)}`;
      else if (f.type === 'image') prompt += `\n\n[Image attached: ${f.name}]`;
    });
    getMSAClient().sendCommand(prompt || content);
  }, [addCard, startStreamMessage]);

  // ── Open file in editor tab ───────────────────────────────────────────────
  const handleOpenFile = useCallback(async node => {
    if (!node || node.type === 'dir') return;
    const existing = tabs.find(t => t.path === node.path);
    if (existing) { setActiveTab(existing.id); return; }
    let content = '';
    try {
      const r = await fetch(`${API}/api/files/read?path=${encodeURIComponent(node.path || node.name)}`);
      if (r.ok) content = (await r.json()).content || '';
    } catch (_) {}
    const id = `file-${Date.now()}`;
    setTabs(p => [...p, { id, name: node.name, path: node.path, type: 'file', content, lang: getExt(node.name) }]);
    setActiveTab(id);
  }, [tabs]);

  const closeTab = useCallback(id => {
    setTabs(p => {
      const next = p.filter(t => t.id !== id);
      if (activeTab === id && next.length > 0) setActiveTab(next[next.length - 1].id);
      return next.length > 0 ? next : [{ id: 'welcome', name: 'Welcome', type: 'welcome' }];
    });
  }, [activeTab]);

  const activeTabData = tabs.find(t => t.id === activeTab);
  const agent = AGENTS.find(a => a.id === activeAgent) || AGENTS[0];

  // ── Sidebar panel content ─────────────────────────────────────────────────
  const SidebarContent = () => {
    if (activity === 'explorer') return <FileExplorer onOpenFile={handleOpenFile} />;
    if (activity === 'career')   return <CareerDashboard />;
    if (activity === 'agents')   return (
      <div className="p-2">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold px-2 py-2 mb-1">Select Agent</div>
        {AGENTS.map(ag => (
          <motion.button key={ag.id} onClick={() => setActiveAgent(ag.id)} whileHover={{ x: 2 }} whileTap={{ scale: 0.97 }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl mb-0.5 transition-all ${
              activeAgent === ag.id ? 'bg-white/10 border border-white/12' : 'hover:bg-white/5 border border-transparent'}`}>
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center bg-gradient-to-br ${ag.bg} flex-shrink-0`}>
              <ag.icon size={15} className="text-white" />
            </div>
            <div className="min-w-0 text-left">
              <div className="text-[12px] font-semibold text-zinc-200">{ag.full}</div>
              <div className="text-[10px] text-zinc-500 truncate">{ag.desc}</div>
            </div>
            {activeAgent === ag.id && <div className="w-1.5 h-1.5 rounded-full ml-auto flex-shrink-0" style={{ backgroundColor: ag.color }} />}
          </motion.button>
        ))}
      </div>
    );
    if (activity === 'search') return (
      <div className="p-3">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold mb-3">Search</div>
        <input placeholder="Search project…" className="w-full bg-zinc-800 border border-white/8 rounded-lg px-3 py-2 text-[12px] text-zinc-300 outline-none focus:border-indigo-500/40" />
        <p className="text-[11px] text-zinc-700 mt-4 text-center">Type to search files and content</p>
      </div>
    );
    if (activity === 'git') return (
      <div className="p-3">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold mb-3">Source Control</div>
        <p className="text-[11px] text-zinc-700">Connect to git repo via backend terminal.</p>
      </div>
    );
    if (activity === 'settings') return (
      <div className="p-3 space-y-3">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold">Settings</div>
        {[['Backend URL','http://localhost:5000'],['Ollama URL','http://localhost:11434'],['Theme','Dark (Obsidian)'],['Font','JetBrains Mono 12px']].map(([k,v]) => (
          <div key={k} className="bg-white/3 border border-white/8 rounded-xl p-3">
            <div className="text-[10px] text-zinc-500 mb-1">{k}</div>
            <div className="text-[12px] text-zinc-200 font-mono">{v}</div>
          </div>
        ))}
      </div>
    );
    return null;
  };

  return (
    <div className="w-screen h-screen bg-[#0a0a0f] text-white overflow-hidden flex flex-col font-sans" style={{ userSelect: 'none' }}>

      {/* ── Title Bar ── */}
      <div className="flex items-center justify-between bg-[#0e0e17] border-b border-white/6 flex-shrink-0 drag" style={{ height: 36 }}>
        <div className="flex items-center gap-3 px-3 no-drag">
          <div className={`w-5 h-5 rounded-lg bg-gradient-to-br ${agent.bg} flex items-center justify-center flex-shrink-0`}>
            <agent.icon size={11} className="text-white" />
          </div>
          <span className="text-[12px] font-bold text-zinc-300">MSA AI Agent V5.0 — Anti-Gravity OS</span>
          <span className="text-[10px] text-zinc-700 border border-zinc-800 px-1.5 py-px rounded-full">IDE</span>
        </div>
        <div className="flex items-center gap-1 px-3 no-drag">
          <button onClick={() => setTerminalOpen(p => !p)}
            className={`p-1.5 rounded text-zinc-600 hover:text-zinc-300 transition-colors ${terminalOpen ? 'text-indigo-400' : ''}`} title="Terminal (Ctrl+`)">
            <Terminal size={13} />
          </button>
          <button onClick={() => setChatOpen(p => !p)}
            className={`p-1.5 rounded text-zinc-600 hover:text-zinc-300 transition-colors ${chatOpen ? 'text-indigo-400' : ''}`} title="AI Chat">
            <MessageSquare size={13} />
          </button>
          <button onClick={() => setCmdOpen(p => !p)}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-white/4 border border-white/8 text-[11px] text-zinc-500 hover:text-zinc-300 transition-all" title="Ctrl+K">
            <Command size={11} /> Ctrl+K
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Activity Bar (leftmost icon strip) ── */}
        <div className="flex flex-col items-center bg-[#0e0e17] border-r border-white/6 flex-shrink-0 py-2 gap-0.5" style={{ width: 48 }}>
          {ACTIVITIES.slice(0, 5).map(act => (
            <button key={act.id}
              onClick={() => { setActivity(act.id); setSidebarOpen(p => activity === act.id ? !p : true); }}
              title={act.title}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all relative group ${
                activity === act.id && sidebarOpen
                  ? 'text-white bg-white/8'
                  : 'text-zinc-600 hover:text-zinc-300 hover:bg-white/5'}`}>
              <act.icon size={18} />
              {activity === act.id && sidebarOpen && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-500 rounded-r-full" />
              )}
              <div className="absolute left-12 hidden group-hover:flex bg-zinc-900 border border-white/10 text-[11px] text-zinc-300 px-2 py-1 rounded-lg whitespace-nowrap z-50 shadow-xl">
                {act.title}
              </div>
            </button>
          ))}
          <div className="flex-1" />
          {ACTIVITIES.slice(5).map(act => (
            <button key={act.id} onClick={() => { setActivity(act.id); setSidebarOpen(true); }}
              title={act.title}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                activity === act.id ? 'text-white bg-white/8' : 'text-zinc-600 hover:text-zinc-300 hover:bg-white/5'}`}>
              <act.icon size={18} />
            </button>
          ))}
          {/* User avatar */}
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center font-bold text-[11px] text-white mt-1 mb-1 cursor-pointer" title="Sadique Amin">
            SA
          </div>
        </div>

        {/* ── Sidebar ── */}
        <AnimatePresence initial={false}>
          {sidebarOpen && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 260, opacity: 1 }} exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="flex-shrink-0 border-r border-white/6 bg-[#0d0d16] overflow-hidden flex flex-col">
              <SidebarContent />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Editor Area ── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Tab bar */}
          {tabs.length > 0 && (
            <TabBar tabs={tabs} active={activeTab} onSelect={setActiveTab} onClose={closeTab} />
          )}
          {/* Editor content */}
          <div className="flex-1 overflow-hidden relative">
            {activeTabData?.type === 'welcome' && (
              <div className="h-full overflow-y-auto">
                <WelcomeScreen onAction={txt => { handleSend(txt); setChatOpen(true); }} />
              </div>
            )}
            {activeTabData?.type === 'file' && (
              <div className="h-full overflow-auto bg-[#0d0d16]" style={{ scrollbarWidth: 'thin', scrollbarColor: '#3f3f46 transparent' }}>
                {/* Lazy Monaco Editor */}
                <React.Suspense fallback={<div className="p-4 text-zinc-600 text-sm font-mono">Loading editor…</div>}>
                  {(() => {
                    try {
                      const { CodeEditor } = require('./components/ui/CodeEditor');
                      return <CodeEditor initialContent={activeTabData.content} language={activeTabData.lang} />;
                    } catch {
                      return (
                        <pre className="p-4 text-zinc-300 text-[12px] font-mono leading-relaxed whitespace-pre-wrap overflow-auto">
                          {activeTabData.content || '(empty file)'}
                        </pre>
                      );
                    }
                  })()}
                </React.Suspense>
              </div>
            )}
          </div>
          {/* Terminal */}
          <AnimatePresence>
            {terminalOpen && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 200, opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
                <TerminalPanel onClose={() => setTerminalOpen(false)} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── AI Chat Panel (right) ── */}
        <AnimatePresence initial={false}>
          {chatOpen && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 380, opacity: 1 }} exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="flex-shrink-0 border-l border-white/6 bg-[#0d0d16] flex flex-col overflow-hidden">
              {/* Chat header — Unified */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-white/8 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-700 flex items-center justify-center">
                    <Sparkles size={12} className="text-white" />
                  </div>
                  <span className="text-[12px] font-bold text-zinc-200">MSA AI IDE</span>
                  <span className="text-[9px] px-1.5 py-px rounded-full border border-green-500/30 text-green-400">● Ready</span>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => useStore.setState({ conversations: [] })}
                    className="p-1.5 rounded text-zinc-600 hover:text-zinc-300 transition-colors" title="Clear chat">
                    <X size={12} />
                  </button>
                  <button onClick={() => setChatOpen(false)} className="p-1.5 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                    <PanelRight size={12} />
                  </button>
                </div>
              </div>
              {/* Unified all-agents header — all 8 agents work as ONE */}
              <div className="px-3 py-2 border-b border-white/6 flex-shrink-0 bg-gradient-to-r from-indigo-950/40 to-violet-950/30">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={11} className="text-indigo-400" />
                    <span className="text-[10px] font-bold text-indigo-300">All Agents Active</span>
                    <span className="text-[9px] px-1.5 py-px rounded-full border border-green-500/30 text-green-400">● All Online</span>
                  </div>
                  <span className="text-[9px] text-zinc-600">Parallel · Auto-route</span>
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  {AGENTS.map(ag => (
                    <div key={ag.id} title={ag.full}
                      className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 cursor-default"
                      style={{ background: `linear-gradient(135deg, ${ag.color}33, ${ag.color}18)`, border: `1px solid ${ag.color}40` }}>
                      <ag.icon size={9} style={{ color: ag.color }} />
                    </div>
                  ))}
                  <span className="text-[9px] text-zinc-700 ml-auto">4 models in parallel</span>
                </div>
              </div>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-3 pt-3 pb-2" style={{ scrollbarWidth: 'thin', scrollbarColor: '#27272a transparent' }}>
                {conversations.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                    <Sparkles size={32} className="text-indigo-400 mb-3" />
                    <p className="text-[12px] text-zinc-500">Start chatting or press<br/><span className="font-mono">Ctrl+K</span> for commands</p>
                    <p className="text-[10px] text-zinc-700 mt-2">Attach any file via 📎</p>
                  </div>
                ) : conversations.map((msg, i) => (
                  <ChatBubble key={msg.id || i} message={msg} agentId={activeAgent} />
                ))}
                <AnimatePresence>
                  {thinkingStatus && <ThinkingDots status={thinkingStatus} />}
                </AnimatePresence>
                <div ref={chatEndRef} />
              </div>
              {/* Composer */}
              <Composer onSend={handleSend} onOpenPalette={() => setCmdOpen(true)} agentId={activeAgent} disabled={!!thinkingStatus} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Status Bar ── */}
      <StatusBar agentId={activeAgent} thinkingStatus={thinkingStatus} modelStatus={modelStatus} />

      {/* ── Command Palette ── */}
      <CmdPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onSubmit={txt => { handleSend(txt); setChatOpen(true); }} />
    </div>
  );
}
