import { useState, useRef, useEffect } from 'react'
import { agentStream } from '../api/client'
import '../styles/chat.css'

interface ProgressCard {
  kind: 'node' | 'tool'
  label: string
  detail?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  cards?: ProgressCard[]
}

interface StreamingMsg {
  cards: ProgressCard[]
  answer: string
}

interface ChatPageProps {
  onFirstMessage?: (title: string) => void
}

export function ChatPage({ onFirstMessage }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState<StreamingMsg | null>(null)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recordedRef = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }

  async function handleSend() {
    const q = input.trim()
    if (!q || streaming !== null) return
    setInput('')
    setError(null)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setMessages(prev => [...prev, { role: 'user', content: q }])

    if (!recordedRef.current && onFirstMessage) {
      recordedRef.current = true
      onFirstMessage(q.slice(0, 40))
    }

    // 本次积累的进度卡和回答（用于最终写入 messages）
    const accCards: ProgressCard[] = []
    let accAnswer = ''

    setStreaming({ cards: [], answer: '' })

    try {
      for await (const evt of agentStream(q)) {
        if (evt.type === 'node_done') {
          accCards.push({ kind: 'node', label: evt.label, detail: evt.detail })
          setStreaming({ cards: [...accCards], answer: accAnswer })

        } else if (evt.type === 'tool_call') {
          const detail = Object.entries(evt.tools)
            .map(([name, count]) => `${name} ×${count}`)
            .join('、')
          accCards.push({ kind: 'tool', label: `已调用工具 ${evt.total} 次`, detail })
          setStreaming({ cards: [...accCards], answer: accAnswer })

        } else if (evt.type === 'answer') {
          accAnswer = evt.content
          setStreaming({ cards: [...accCards], answer: accAnswer })

        } else if (evt.type === 'error') {
          setError(evt.content)
        }
        // 'start' 和 'done' 无需处理，for-await 结束时自然退出
      }

      // 流结束，写入最终消息
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: accAnswer || '（未收到回答）',
          cards: accCards.length > 0 ? accCards : undefined,
        },
      ])
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setStreaming(null)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const loading = streaming !== null

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

  if (messages.length === 0 && streaming === null) {
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
            {msg.role === 'assistant' ? (
              <div className="message-content">
                {msg.cards && msg.cards.length > 0 && (
                  <div className="progress-list">
                    {msg.cards.map((card, j) => (
                      <ProgressCardView key={j} card={card} />
                    ))}
                  </div>
                )}
                <div className="message-bubble">{msg.content}</div>
              </div>
            ) : (
              <div className="message-bubble">{msg.content}</div>
            )}
          </div>
        ))}

        {/* 流式进行中的消息 */}
        {streaming !== null && (
          <div className="message message-assistant">
            <div className="message-content">
              {streaming.cards.length > 0 && (
                <div className="progress-list">
                  {streaming.cards.map((card, j) => (
                    <ProgressCardView key={j} card={card} active />
                  ))}
                </div>
              )}
              {streaming.answer ? (
                <div className="message-bubble">{streaming.answer}</div>
              ) : (
                <div className="message-bubble loading">
                  <span className="dot" /><span className="dot" /><span className="dot" />
                </div>
              )}
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

// ── 进度卡片组件 ──────────────────────────────────────────────
function ProgressCardView({ card, active }: { card: ProgressCard; active?: boolean }) {
  const icon = card.kind === 'tool' ? '⚙' : '✓'
  return (
    <div className={`progress-card${active ? ' progress-card-active' : ''}`}>
      <span className="progress-card-icon">{icon}</span>
      <span className="progress-card-label">{card.label}</span>
      {card.detail && (
        <span className="progress-card-detail">{card.detail}</span>
      )}
    </div>
  )
}
