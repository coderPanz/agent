import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'
import '../styles/chat.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPageProps {
  onFirstMessage?: (title: string) => void
}

export function ChatPage({ onFirstMessage }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recordedRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }

  async function handleSend() {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    setError(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setMessages(prev => [...prev, { role: 'user', content: q }])

    if (!recordedRef.current && onFirstMessage) {
      recordedRef.current = true
      onFirstMessage(q.slice(0, 40))
    }

    setLoading(true)
    try {
      const result = await api.agentChat(q)
      setMessages(prev => [...prev, { role: 'assistant', content: result.answer }])
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const inputBox = (placeholder: string, rows: number) => (
    <div className="chat-input-box">
      <textarea
        ref={textareaRef}
        className="chat-input"
        value={input}
        rows={rows}
        placeholder={placeholder}
        disabled={loading}
        onChange={e => { setInput(e.target.value); autoResize() }}
        onKeyDown={handleKeyDown}
      />
      <div className="chat-input-actions">
        <button className="send-btn" onClick={handleSend} disabled={loading || !input.trim()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </div>
  )

  if (messages.length === 0) {
    return (
      <div className="chat-welcome">
        <h1 className="welcome-title">有什么我可以帮你的？</h1>
        {inputBox('向 AI 提问，使用 @ 引用文件', 3)}
      </div>
    )
  }

  return (
    <div className="chat-layout">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <div className="message-bubble">{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-bubble loading">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}

        {error && <div className="chat-error">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <footer className="chat-footer">
        {inputBox('继续提问...', 1)}
      </footer>
    </div>
  )
}
