import React, { useEffect, useRef, useState } from 'react';
import { useStore } from './core/stateStore';
import { GatewayWebSocketClient } from './core/apiClient';
import { SpatialCanvas } from './components/ui/SpatialCanvas';
import { ChatCard } from './components/ui/ChatCard';
import { AgentConstellation } from './components/ui/AgentConstellation';
import { FloatingInputBar } from './components/ui/FloatingInputBar';

export default function App() {
  const { conversations, addCard, setAgentStatus } = useStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeModel, setActiveModel] = useState('Ollama (Local Llama3)');
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new GatewayWebSocketClient("ws://localhost:8080/stream");
    wsRef.current = ws;

    ws.onConnect(() => {
      console.log("Gateway WebSocket connected!");
    });

    ws.onMessage((data) => {
      if (data.agent) {
        setAgentStatus(data.agent, data.status || 'idle');
      }
      if (data.content) {
        addCard({
          role: data.agent || 'assistant',
          content: data.content
        });
      }
    });

    ws.connect();

    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const query = prompt("Enter command palette query:");
        if (query) handleSend(query);
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [addCard, setAgentStatus]);

  const handleSend = (text) => {
    addCard({
      role: 'user',
      content: text
    });

    if (wsRef.current) {
      wsRef.current.send({
        action: 'execute',
        query: text
      });
    }
  };

  const clearCanvas = () => {
    useStore.setState({ conversations: [] });
  };

  return (
    <div className="w-screen h-screen relative bg-zinc-950 text-white overflow-hidden font-sans flex">
      
      {/* 🚀 Modern Sidebar (ChatGPT / Claude Style) */}
      <div 
        className={`h-screen bg-zinc-900/80 border-r border-white/10 backdrop-blur-2xl transition-all duration-300 z-50 flex flex-col justify-between ${
          sidebarOpen ? 'w-64' : 'w-0 overflow-hidden border-r-0'
        }`}
      >
        <div className="p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold tracking-wider text-indigo-400">MSA AI OPERATING SYSTEM</span>
            <button 
              onClick={() => setSidebarOpen(false)}
              className="text-xs text-zinc-500 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <div className="text-[10px] uppercase text-zinc-500 font-bold tracking-wider">Active Workspace</div>
            <div className="p-3 bg-white/5 border border-white/10 rounded-xl text-xs flex items-center gap-2 hover:bg-white/10 cursor-pointer">
              <span>📁</span>
              <span className="font-semibold truncate">msa_agent_root</span>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <div className="text-[10px] uppercase text-zinc-500 font-bold tracking-wider">Control Panel</div>
            <button 
              onClick={clearCanvas}
              className="w-full text-left p-2.5 hover:bg-red-500/10 hover:text-red-400 border border-white/5 rounded-xl text-xs transition-all flex items-center gap-2"
            >
              <span>🗑️</span> Clear Canvas
            </button>
          </div>
        </div>

        <div className="p-4 border-t border-white/5 flex items-center gap-3 bg-black/20">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-sm">
            SA
          </div>
          <div className="flex flex-col truncate">
            <span className="text-xs font-bold">Sadique Amin</span>
            <span className="text-[9px] text-zinc-500">Software Engineer</span>
          </div>
        </div>
      </div>

      {/* Button to reopen sidebar when collapsed */}
      {!sidebarOpen && (
        <button 
          onClick={() => setSidebarOpen(true)}
          className="fixed left-4 top-4 z-50 p-2.5 bg-zinc-900/80 border border-white/10 rounded-xl hover:bg-white/5 transition-colors cursor-pointer text-xs"
        >
          ☰
        </button>
      )}

      {/* Main Workspace Frame */}
      <div className="flex-1 h-screen relative flex flex-col">
        
        {/* 🚀 Top Bar (Model / Provider Selection Bar) */}
        <div className="fixed top-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-zinc-900/60 backdrop-blur-md border border-white/10 rounded-full flex items-center gap-4 z-40 shadow-xl">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span className="text-[10px] font-bold text-zinc-400">ENGINE SOURCE:</span>
          </div>
          <select 
            value={activeModel} 
            onChange={(e) => setActiveModel(e.target.value)}
            className="bg-transparent text-xs text-white font-semibold focus:outline-none cursor-pointer"
          >
            <option className="bg-zinc-900 text-white" value="Ollama (Local Llama3)">Ollama (Local Llama3)</option>
            <option className="bg-zinc-900 text-white" value="Gemini API (Cloud 1.5)">Gemini API (Cloud 1.5)</option>
            <option className="bg-zinc-900 text-white" value="Local GGUF (llama.cpp)">Local GGUF (llama.cpp)</option>
            <option className="bg-zinc-900 text-white" value="Simulate/Offline NLP">Simulate/Offline NLP</option>
          </select>
        </div>

        {/* Infinite Grid Panning Canvas */}
        <SpatialCanvas>
          {conversations.map((card) => (
            <ChatCard key={card.id} card={card} />
          ))}
        </SpatialCanvas>

        {/* Agent constellation (Right indicators instead of overlapping sidebar) */}
        <AgentConstellation />
        
        {/* Floating Input Composer */}
        <FloatingInputBar onSend={handleSend} />
      </div>
    </div>
  );
}
