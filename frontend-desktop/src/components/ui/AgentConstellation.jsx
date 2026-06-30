import React from 'react';
import { useStore } from '../../core/stateStore';
import { AgentAvatars } from '../assets/agent-avatars';

export function AgentConstellation() {
  const { agents } = useStore();

  return (
    <div className="fixed left-6 top-1/2 -translate-y-1/2 flex flex-col gap-4 p-3 bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50">
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

            {/* Tooltip name */}
            <div className="absolute left-14 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 border border-white/10 text-[10px] text-white px-2 py-1 rounded-lg pointer-events-none capitalize">
              {name} ({config.status})
            </div>
          </div>
        );
      })}
    </div>
  );
}
