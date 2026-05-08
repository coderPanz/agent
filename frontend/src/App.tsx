import { useState, useRef, useEffect } from 'react'
import { KnowledgeBaseManager } from './pages/KnowledgeBaseManager'
import { api } from './api/client'
import './App.css'

type Mode = 'agentic' | 'common'
type Page = 'chat' | 'kb'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function App() {
  const [page, setPage] = useState<Page>('chat')
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
      const answer = await api.ragSearch({ query: q, mode })
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
    <div className="app-container">
      {/* 导航栏 */}
      <nav className="app-nav">
        <div className="app-nav-inner">
          <h1 className="app-title">My Agent</h1>
          <div className="app-nav-tabs">
            <button
              className={`nav-tab${page === 'chat' ? ' active' : ''}`}
              onClick={() => setPage('chat')}
            >
              💬 Chat
            </button>
            <button
              className={`nav-tab${page === 'kb' ? ' active' : ''}`}
              onClick={() => setPage('kb')}
            >
              📚 知识库
            </button>
          </div>
        </div>
      </nav>

      {/* 页面内容 */}
      <div className="app-content">
        {page === 'chat' ? (
          <div className="chat-layout">
            <header className="chat-header">
              <h2>RAG 问答</h2>
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
        ) : (
          <KnowledgeBaseManager />
        )}
      </div>
    </div>
  )
}
