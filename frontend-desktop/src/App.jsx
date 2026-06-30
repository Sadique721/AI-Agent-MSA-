import React, { useEffect, useRef } from 'react';
import { useStore } from './core/stateStore';
import { GatewayWebSocketClient } from './core/apiClient';
import { SpatialCanvas } from './components/ui/SpatialCanvas';
import { ChatCard } from './components/ui/ChatCard';
import { AgentConstellation } from './components/ui/AgentConstellation';
import { FloatingInputBar } from './components/ui/FloatingInputBar';

export default function App() {
  const { conversations, addCard, setAgentStatus } = useStore();
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket Gateway
    const ws = new GatewayWebSocketClient("ws://localhost:8080/stream");
    wsRef.current = ws;

    ws.onConnect(() => {
      console.log("Gateway WebSocket connected!");
    });

    ws.onMessage((data) => {
      // Message format: { agent: 'coder', status: 'active', content: '...' }
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

    // Hotkey listener Ctrl+K
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        alert("Command Palette triggered! Enter your query.");
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [addCard, setAgentStatus]);

  const handleSend = (text) => {
    // Add User card immediately
    addCard({
      role: 'user',
      content: text
    });

    // Send payload to Gateway WebSocket
    if (wsRef.current) {
      wsRef.current.send({
        action: 'execute',
        query: text
      });
    }
  };

  return (
    <div className="w-screen h-screen relative bg-zinc-950 text-white overflow-hidden font-sans">
      {/* Background radial cosmic glow overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/20 via-zinc-950 to-zinc-950 pointer-events-none z-0" />

      {/* Infinite Grid Panning Canvas */}
      <SpatialCanvas>
        {conversations.map((card) => (
          <ChatCard key={card.id} card={card} />
        ))}
      </SpatialCanvas>

      {/* Ambient Controllers Overlay */}
      <AgentConstellation />
      
      {/* Floating Input Controller */}
      <FloatingInputBar onSend={handleSend} />
    </div>
  );
}
