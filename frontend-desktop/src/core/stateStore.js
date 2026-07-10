import { create } from 'zustand';

export const useStore = create((set) => ({
  // Agents states
  agents: {
    planner: { status: 'idle', color: '#3b82f6' },
    coder: { status: 'idle', color: '#06b6d4' },
    researcher: { status: 'idle', color: '#10b981' },
    browser: { status: 'idle', color: '#f59e0b' },
    validator: { status: 'idle', color: '#8b5cf6' }
  },
  
  // Conversations cards array
  conversations: [
    {
      id: 'c1',
      role: 'user',
      content: 'Welcome to MSA Agent Desktop Client. Drag me anywhere on the infinite canvas!',
      x: 100,
      y: 150
    }
  ],

  // Canvas coordinates
  canvasPosition: { x: 0, y: 0, scale: 1 },

  // Set individual agent status
  setAgentStatus: (agentName, status) => set((state) => ({
    agents: {
      ...state.agents,
      [agentName]: { ...state.agents[agentName], status }
    }
  })),

  // Update canvas coordinates
  setCanvasPosition: (x, y, scale) => set({
    canvasPosition: { x, y, scale }
  }),

  // Add conversation card
  addCard: (card) => set((state) => ({
    conversations: [...state.conversations, {
      id: `card_${Date.now()}`,
      x: 200 + (state.conversations.length * 30),
      y: 200 + (state.conversations.length * 20),
      ...card
    }]
  })),

  // Update specific card coordinates/content
  updateCard: (id, updates) => set((state) => ({
    conversations: state.conversations.map((card) =>
      card.id === id ? { ...card, ...updates } : card
    )
  })),

  addStreamToken: (token) => set((state) => {
    const conv = [...state.conversations];
    const last = conv[conv.length - 1];
    if (last && last.role === 'assistant' && last.streaming) {
      conv[conv.length - 1] = { ...last, content: last.content + token };
    }
    return { conversations: conv };
  }),

  startStreamMessage: () => set((state) => ({
    conversations: [...state.conversations, {
      id: `stream_${Date.now()}`,
      role: 'assistant',
      content: '',
      streaming: true,
      timestamp: new Date().toISOString(),
      x: 200 + (state.conversations.length * 30),
      y: 200 + (state.conversations.length * 20),
    }]
  })),

  finalizeStreamMessage: (fullText) => set((state) => {
    const conv = [...state.conversations];
    const idx = conv.findLastIndex(m => m.role === 'assistant' && m.streaming);
    if (idx >= 0) {
      conv[idx] = { ...conv[idx], content: fullText || conv[idx].content, streaming: false };
    }
    return { conversations: conv };
  })
}));
