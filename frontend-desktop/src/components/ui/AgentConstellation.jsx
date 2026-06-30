import React from 'react';
import { useStore } from '../../core/stateStore';
import { AgentAvatars } from '../assets/agent-avatars';

export function AgentConstellation() {
  const { agents } = useStore();

  const activeAgents = Object.entries(agents).filter(([_, config]) => config.status === 'active');

  return (
    <>
      {/* Constellation Panel positioned cleanly on the RIGHT */}
      <div className="fixed right-6 top-1/2 -translate-y-1/2 flex flex-col gap-4 p-3 bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50">
        <div className="text-[9px] uppercase font-bold text-zinc-500 text-center tracking-wider border-b border-white/5 pb-1 select-none">
          AGENTS
        </div>
        {Object.entries(agents).map(([name, config]) => {
          const renderAvatar = AgentAvatars[name];
          return (
            <div
              key={name}
              title={`${name} Status: ${config.status}`}
              className="group relative flex items-center justify-center p-2 rounded-xl hover:bg-white/5 cursor-pointer transition-all"
            >
              {renderAvatar(config.color)}
              
              {/* Status indicator ring */}
              <div
                className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-zinc-950 transition-all duration-300"
                style={{
                  backgroundColor: config.status === 'active' ? '#10b981' : '#71717a'
                }}
              />

              {/* Tooltip name (Positioned left of the icon since constellation is on the right) */}
              <div className="absolute right-14 opacity-0 group-hover:opacity-100 transition-opacity bg-black/90 border border-white/10 text-[10px] text-white px-2 py-1 rounded-lg pointer-events-none capitalize whitespace-nowrap z-50">
                {name} ({config.status})
              </div>
            </div>
          );
        })}
      </div>

      {/* Realtime execution logs panel (shows active agent tasks at bottom right) */}
      {activeAgents.length > 0 && (
        <div className="fixed bottom-24 right-6 p-3 bg-zinc-900/80 backdrop-blur-md border border-white/10 rounded-xl max-w-[240px] z-50 flex flex-col gap-1.5 shadow-2xl animate-bounce">
          <div className="text-[9px] uppercase tracking-wider font-bold text-zinc-500">Executing Subroutines</div>
          {activeAgents.map(([name]) => (
            <div key={name} className="flex items-center gap-2 text-[10px] text-zinc-300">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
              <span className="capitalize">{name} Agent</span> calling local modules...
            </div>
          ))}
        </div>
      )}
    </>
  );
}
