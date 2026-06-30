import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Persona {
  name: string
  display_name: string
  description: string
  tone: string
  reasoning_mode: string
  avatar_color: string
}

interface SettingsStore {
  currentPersona: string
  personas: Record<string, Persona>
  currentWorkspace: string
  theme: 'dark' | 'light'
  streamingEnabled: boolean
  backendUrl: string
  setPersona: (name: string) => void
  setPersonas: (personas: Record<string, Persona>) => void
  setWorkspace: (id: string) => void
  setBackendUrl: (url: string) => void
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      currentPersona: 'default',
      personas: {
        default: {
          name: 'default',
          display_name: 'MSA AI Assistant',
          description: 'Balanced, helpful AI assistant',
          tone: 'professional',
          reasoning_mode: 'balanced',
          avatar_color: '#6366f1',
        },
        developer: {
          name: 'developer',
          display_name: 'Senior Developer',
          description: 'Expert software engineer',
          tone: 'technical',
          reasoning_mode: 'coding',
          avatar_color: '#10b981',
        },
        researcher: {
          name: 'researcher',
          display_name: 'Research Analyst',
          description: 'Deep research with citations',
          tone: 'academic',
          reasoning_mode: 'research',
          avatar_color: '#8b5cf6',
        },
      },
      currentWorkspace: 'default',
      theme: 'dark',
      streamingEnabled: true,
      backendUrl: 'http://localhost:5000',

      setPersona: (name) => set({ currentPersona: name }),
      setPersonas: (personas) => set({ personas }),
      setWorkspace: (id) => set({ currentWorkspace: id }),
      setBackendUrl: (url) => set({ backendUrl: url }),
    }),
    { name: 'msa-settings' }
  )
)
