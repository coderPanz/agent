import { useState, useRef, useEffect } from 'react'
import './App.css'

type Mode = 'agentic' | 'common'
interface Message {
  role: 'user' | 'assistant'
  content: string
}

async function ragSearch(query: string, mode: Mode): Promise<string> {
  const res = await fetch('/api/rag_search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, mode }),
  })
  if (!res.ok) throw new Error(`请求失败 (HTTP ${res.status})`)
  const data = await res.json()
  return data.answer
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<Mode>('agentic')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
    setLoading(true)
    try {
      const answer = await ragSearch(q, mode)
      setMessages(prev => [...prev, { role: 'assistant', content: answer }])
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误')
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

  return (
    <div className="chat-layout">
      <header className="chat-header">
        <h1>RAG 知识库问答</h1>
        <div className="mode-selector">
          <button
            className={`mode-btn${mode === 'agentic' ? ' active' : ''}`}
            onClick={() => setMode('agentic')}
          >
            Agentic
          </button>
          <button
            className={`mode-btn${mode === 'common' ? ' active' : ''}`}
            onClick={() => setMode('common')}
          >
            Common
          </button>
        </div>
      </header>

      <main className="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="chat-empty">
            <strong>开始提问</strong>
            输入问题，从知识库中检索答案
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <div className="message-bubble">{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-bubble loading">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}

        {error && <div className="chat-error">{error}</div>}
        <div ref={bottomRef} />
      </main>

      <footer className="chat-input-area">
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={input}
          rows={1}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          disabled={loading}
          onChange={e => { setInput(e.target.value); autoResize() }}
          onKeyDown={handleKeyDown}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          发送
        </button>
      </footer>
    </div>
  )
}
