import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  stage?: string
  timestamp: number
  model?: string
  reflectionScore?: number
}

export interface AgentStage {
  state: 'idle' | 'thinking' | 'searching' | 'running_tool' | 'generating' | 'reflecting' | 'error'
  message: string
}

interface ChatStore {
  messages: Message[]
  stage: AgentStage
  isStreaming: boolean
  addMessage: (msg: Omit<Message, 'id' | 'timestamp'>) => string
  appendToken: (id: string, token: string) => void
  finalizeMessage: (id: string, extras?: Partial<Message>) => void
  setStage: (stage: AgentStage) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  stage: { state: 'idle', message: 'Ready' },
  isStreaming: false,

  addMessage: (msg) => {
    const id = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    set(state => ({
      messages: [...state.messages, { ...msg, id, timestamp: Date.now() }]
    }))
    return id
  },

  appendToken: (id, token) => {
    set(state => ({
      messages: state.messages.map(m =>
        m.id === id ? { ...m, content: m.content + token, streaming: true } : m
      )
    }))
  },

  finalizeMessage: (id, extras) => {
    set(state => ({
      messages: state.messages.map(m =>
        m.id === id ? { ...m, streaming: false, stage: undefined, ...extras } : m
      )
    }))
  },

  setStage: (stage) => {
    set({ stage, isStreaming: stage.state !== 'idle' && stage.state !== 'error' })
  },

  clearMessages: () => {
    set({ messages: [], stage: { state: 'idle', message: 'Ready' }, isStreaming: false })
  },
}))
