import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChatStore } from './store/chatStore'
import { useSettingsStore } from './store/settingsStore'
import { renderMarkdown } from './utils/markdown'
import './index.css'

// ── Suggestion Cards ──────────────────────────────────────────────────────────
const SUGGESTIONS = [
  { icon: '⚡', text: 'Write a FastAPI endpoint with authentication' },
  { icon: '🔍', text: 'Explain how RAG systems work' },
  { icon: '🐛', text: 'Debug my Python traceback error' },
  { icon: '📊', text: 'Create a data analysis script with pandas' },
  { icon: '🏗️', text: 'Design a microservices architecture' },
  { icon: '🔒', text: 'Review my code for security vulnerabilities' },
]

// ── Personas ──────────────────────────────────────────────────────────────────
const PERSONA_LIST = [
  { name: 'default',   label: 'MSA',     color: '#6366f1', icon: '🤖' },
  { name: 'developer', label: 'Dev',     color: '#10b981', icon: '💻' },
  { name: 'architect', label: 'Arch',    color: '#f59e0b', icon: '🏗️' },
  { name: 'researcher',label: 'Dr',      color: '#8b5cf6', icon: '🔬' },
  { name: 'teacher',   label: 'Prof',    color: '#3b82f6', icon: '📚' },
  { name: 'writer',    label: 'Scribe',  color: '#ec4899', icon: '✍️' },
  { name: 'devops',    label: 'DevOps',  color: '#f97316', icon: '🚀' },
  { name: 'security',  label: 'SecOps',  color: '#ef4444', icon: '🔐' },
]

// ── Stage config ──────────────────────────────────────────────────────────────
const STAGE_CONFIG: Record<string, { label: string; icon: string }> = {
  idle:        { label: 'Ready',              icon: '✓' },
  thinking:    { label: 'Thinking...',         icon: '💭' },
  searching:   { label: 'Searching knowledge', icon: '🔍' },
  running_tool:{ label: 'Running tools',       icon: '⚡' },
  generating:  { label: 'Generating',          icon: '✨' },
  reflecting:  { label: 'Reviewing quality',   icon: '🔄' },
  error:       { label: 'Error',               icon: '⚠️' },
}

// ── API Helper ────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:5000'
const V5_BASE  = 'http://localhost:8000'

async function sendMessage(
  command: string,
  persona: string,
  onToken: (token: string) => void,
  onStage: (state: string, msg: string) => void,
): Promise<{ response: string; action: string }> {
  // Try SSE streaming from V5 gateway first
  try {
    const url = `${V5_BASE}/api/v5/stream?command=${encodeURIComponent(command)}&persona=${persona}`
    const source = new EventSource(url)
    return await new Promise((resolve, reject) => {
      let fullResponse = ''
      const timeout = setTimeout(() => {
        source.close()
        reject(new Error('Stream timeout'))
      }, 90000)

      source.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.type === 'token') {
            fullResponse += data.content
            onToken(data.content)
          } else if (data.type === 'status') {
            onStage(data.state, data.message)
          } else if (data.type === 'completed') {
            clearTimeout(timeout)
            source.close()
            resolve({ response: data.response || fullResponse, action: data.action || 'chat' })
          } else if (data.type === 'error') {
            clearTimeout(timeout)
            source.close()
            reject(new Error(data.message))
          }
        } catch { /* skip parse errors */ }
      }
      source.onerror = () => {
        clearTimeout(timeout)
        source.close()
        reject(new Error('SSE connection failed'))
      }
    })
  } catch {
    // Fallback to Flask
    onStage('generating', 'Connecting to backend...')
    const resp = await fetch(`${API_BASE}/api/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, persona }),
    })
    if (!resp.ok) throw new Error(`Backend error: ${resp.status}`)
    const data = await resp.json()
    const text = data.response || data.message || 'No response'
    // Simulate streaming for fallback
    const words = text.split(' ')
    for (const word of words) {
      onToken(word + ' ')
      await new Promise(r => setTimeout(r, 18))
    }
    return { response: text, action: data.action || 'chat' }
  }
}

// ── Message Component ─────────────────────────────────────────────────────────
const MessageBubble = React.memo(({ message }: { message: any }) => {
  const isUser = message.role === 'user'
  const html = isUser ? undefined : renderMarkdown(message.content)

  return (
    <motion.div
      className={`message-row message-${message.role}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
    >
      {/* Stage badge for assistant */}
      {!isUser && message.stage && (
        <div className="stage-badge">
          <span className="stage-icon">{STAGE_CONFIG[message.stage]?.icon || '•'}</span>
          <span>{STAGE_CONFIG[message.stage]?.label || message.stage}</span>
        </div>
      )}

      <div className={`message-bubble ${message.role}`}>
        {isUser ? (
          <span>{message.content}</span>
        ) : (
          <>
            {message.content ? (
              <div
                className="markdown-body"
                dangerouslySetInnerHTML={{ __html: html! }}
              />
            ) : (
              <div className="thinking-dots">
                <div className="thinking-dot" />
                <div className="thinking-dot" />
                <div className="thinking-dot" />
              </div>
            )}
            {message.streaming && <span className="streaming-cursor" />}
          </>
        )}
      </div>

      {/* Timestamp */}
      <span style={{ fontSize: 10, color: 'var(--text-muted)', padding: '0 4px' }}>
        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        {!isUser && message.model && message.model !== 'error' && (
          <span style={{ marginLeft: 6 }}>· {message.model}</span>
        )}
      </span>
    </motion.div>
  )
})

// ── Persona Switcher Component ────────────────────────────────────────────────
const PersonaSwitcher = ({
  current, onSelect
}: { current: string; onSelect: (name: string) => void }) => {
  const [open, setOpen] = useState(false)
  const p = PERSONA_LIST.find(x => x.name === current) || PERSONA_LIST[0]

  return (
    <div style={{ position: 'relative' }}>
      <button className="persona-chip" onClick={() => setOpen(o => !o)}>
        <span>{p.icon}</span>
        <span>{p.label}</span>
        <span style={{ fontSize: 10 }}>▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="persona-menu"
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ duration: 0.15 }}
          >
            {PERSONA_LIST.map(persona => (
              <div
                key={persona.name}
                className={`persona-menu-item ${current === persona.name ? 'active' : ''}`}
                onClick={() => { onSelect(persona.name); setOpen(false) }}
              >
                <div
                  className="persona-avatar"
                  style={{ background: `linear-gradient(135deg, ${persona.color}, ${persona.color}99)` }}
                >
                  {persona.icon}
                </div>
                <div className="persona-info">
                  <div className="persona-name">{persona.label}</div>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Sidebar Component ─────────────────────────────────────────────────────────
const Sidebar = ({ onNewChat }: { onNewChat: () => void }) => (
  <div className="sidebar">
    <div className="sidebar-header">
      <div className="sidebar-logo">✦</div>
      <div>
        <div className="sidebar-title">MSA AI</div>
        <div className="sidebar-subtitle">V5.0 Anti-Gravity</div>
      </div>
    </div>

    <div className="sidebar-body">
      <button className="new-chat-btn" onClick={onNewChat}>
        <span>✦</span>
        <span>New Conversation</span>
      </button>

      <div className="sidebar-section-label">Tools</div>
      {[
        { icon: '🔍', label: 'RAG Search' },
        { icon: '🌐', label: 'Web Research' },
        { icon: '💻', label: 'Code Execution' },
        { icon: '📁', label: 'File Manager' },
        { icon: '🔧', label: 'Git Operations' },
      ].map(item => (
        <button key={item.label} className="sidebar-item">
          <span className="sidebar-item-icon">{item.icon}</span>
          <span className="sidebar-item-text">{item.label}</span>
        </button>
      ))}

      <div className="sidebar-section-label">Workspaces</div>
      {['Default', 'Frontend', 'Backend', 'Research'].map((ws, i) => (
        <button key={ws} className={`sidebar-item ${i === 0 ? 'active' : ''}`}>
          <span className="sidebar-item-icon">📂</span>
          <span className="sidebar-item-text">{ws}</span>
        </button>
      ))}
    </div>

    <div className="sidebar-footer">
      <button className="sidebar-item" style={{ width: '100%' }}>
        <span className="sidebar-item-icon">⚙️</span>
        <span className="sidebar-item-text">Settings</span>
      </button>
      <button className="sidebar-item" style={{ width: '100%' }}>
        <span className="sidebar-item-icon">📊</span>
        <span className="sidebar-item-text">Telemetry</span>
      </button>
    </div>
  </div>
)

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const { messages, stage, addMessage, appendToken, finalizeMessage, setStage, clearMessages } = useChatStore()
  const { currentPersona, setPersona } = useSettingsStore()

  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const assistantMsgIdRef = useRef<string | null>(null)

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [input])

  const handleSend = useCallback(async () => {
    const query = input.trim()
    if (!query || isLoading) return

    setInput('')
    setIsLoading(true)

    // Add user message
    addMessage({ role: 'user', content: query })

    // Add placeholder assistant message
    const aId = addMessage({ role: 'assistant', content: '', streaming: true, stage: 'thinking' })
    assistantMsgIdRef.current = aId

    setStage({ state: 'thinking', message: 'Processing request...' })

    try {
      const { response } = await sendMessage(
        query,
        currentPersona,
        (token) => {
          appendToken(aId, token)
        },
        (state, message) => {
          setStage({ state: state as any, message })
          // Update the message's stage indicator
          useChatStore.setState(s => ({
            messages: s.messages.map(m => m.id === aId ? { ...m, stage: state } : m)
          }))
        },
      )
      finalizeMessage(aId, { stage: undefined })
      setStage({ state: 'idle', message: 'Ready' })
    } catch (err: any) {
      finalizeMessage(aId, {
        content: `**Error:** ${err.message || 'Connection failed. Ensure the backend is running.'}`,
        streaming: false,
        stage: undefined,
      })
      setStage({ state: 'error', message: err.message })
      setTimeout(() => setStage({ state: 'idle', message: 'Ready' }), 3000)
    } finally {
      setIsLoading(false)
      assistantMsgIdRef.current = null
      textareaRef.current?.focus()
    }
  }, [input, isLoading, currentPersona, addMessage, appendToken, finalizeMessage, setStage])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = (text: string) => {
    setInput(text)
    textareaRef.current?.focus()
  }

  const stageInfo = STAGE_CONFIG[stage.state] || STAGE_CONFIG.idle
  const currentPersonaObj = PERSONA_LIST.find(p => p.name === currentPersona) || PERSONA_LIST[0]

  return (
    <div className="app-layout">
      {/* Animated background */}
      <div className="bg-ambient">
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />
        <div className="bg-orb bg-orb-3" />
      </div>

      {/* Sidebar */}
      <Sidebar onNewChat={clearMessages} />

      {/* Main chat area */}
      <div className="main-area">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-left">
            <div className="chat-header-title">
              {currentPersonaObj.icon} {currentPersonaObj.label === 'MSA' ? 'MSA AI Agent' : currentPersonaObj.label}
            </div>
            <div className={`agent-status ${stage.state}`}>
              <div className="agent-status-dot" />
              <span>{stageInfo.icon} {stageInfo.label}</span>
            </div>
          </div>
          <div className="chat-header-right">
            <button className="header-btn" title="Clear chat" onClick={clearMessages}>🗑</button>
            <button className="header-btn" title="Export">📤</button>
            <button className="header-btn" title="Settings">⚙️</button>
          </div>
        </div>

        {/* Messages */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <motion.div
              className="empty-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="empty-state-logo">✦</div>
              <div>
                <div className="empty-state-title">MSA AI Agent V5.0</div>
                <div className="empty-state-subtitle">
                  Anti-Gravity Desktop AI OS — powered by local LLMs, hybrid RAG, and multi-agent orchestration.
                </div>
              </div>
              <div className="suggestion-grid">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={i}
                    className="suggestion-card"
                    onClick={() => handleSuggestion(s.text)}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                  >
                    <span className="suggestion-icon">{s.icon}</span>
                    {s.text}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          ) : (
            <div className="messages-inner">
              <AnimatePresence>
                {messages.map(msg => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </AnimatePresence>
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="input-area">
          <div className="input-wrapper">
            <div className="input-box">
              <textarea
                ref={textareaRef}
                className="input-field"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`Message ${currentPersonaObj.label === 'MSA' ? 'MSA AI' : currentPersonaObj.label}... (Enter to send, Shift+Enter for newline)`}
                rows={1}
                disabled={isLoading}
                autoFocus
              />
              <motion.button
                className="send-btn"
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                whileTap={{ scale: 0.9 }}
                title="Send (Enter)"
              >
                {isLoading ? '⏳' : '↑'}
              </motion.button>
            </div>

            <div className="input-footer">
              <span className="input-hint">
                {isLoading ? `${stageInfo.icon} ${stage.message}` : 'Enter ↵ to send · Shift+Enter for newline'}
              </span>
              <div className="input-actions">
                <button className="input-action-btn" title="Attach file">📎</button>
                <button className="input-action-btn" title="Voice input">🎙</button>
                <PersonaSwitcher current={currentPersona} onSelect={setPersona} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
