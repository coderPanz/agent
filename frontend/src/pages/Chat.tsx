import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { agentStream, type ReActStep, type ToolDetail } from '../api/client'
import '../styles/chat.css'

// ── 数据结构 ──────────────────────────────────────────────────

interface ExecutionCard {
  name: string
  label: string
  detail?: string
  elapsed_ms?: number
  steps?: ReActStep[]
  tool_details?: ToolDetail[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  cards?: ExecutionCard[]
}

interface StreamingMsg {
  cards: ExecutionCard[]
  answer: string
}

interface ChatPageProps {
  onFirstMessage?: (title: string) => void
}

// ── 工具函数 ──────────────────────────────────────────────────

function formatElapsed(ms?: number): string {
  if (!ms || ms <= 0) return ''
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
}

const NODE_ICONS: Record<string, string> = {
  router:          '⚡',
  context_builder: '◈',
  react_executor:  '⊕',
  critic:          '✓',
  memory_write:    '◎',
  chat:            '◈',
}

// ── 主组件 ────────────────────────────────────────────────────

export function ChatPage({ onFirstMessage }: ChatPageProps) {
  const [messages, setMessages]   = useState<Message[]>([])
  const [input, setInput]         = useState('')
  const [streaming, setStreaming] = useState<StreamingMsg | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const bottomRef                 = useRef<HTMLDivElement>(null)
  const textareaRef               = useRef<HTMLTextAreaElement>(null)
  const recordedRef               = useRef(false)

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

    const accCards: ExecutionCard[] = []
    let accAnswer = ''
    setStreaming({ cards: [], answer: '' })

    try {
      for await (const evt of agentStream(q)) {
        if (evt.type === 'node_done') {
          accCards.push({
            name:         evt.name,
            label:        evt.label,
            detail:       evt.detail,
            elapsed_ms:   evt.elapsed_ms,
            steps:        evt.steps,
            tool_details: evt.tool_details,
          })
          setStreaming({ cards: [...accCards], answer: accAnswer })

        } else if (evt.type === 'answer') {
          accAnswer = evt.content
          setStreaming({ cards: [...accCards], answer: accAnswer })

        } else if (evt.type === 'error') {
          setError(evt.content)
        }
        // tool_call 事件已内嵌到 node_done，不再单独创建卡片
      }

      setMessages(prev => [
        ...prev,
        {
          role:    'assistant',
          content: accAnswer || '（未收到回答）',
          cards:   accCards.length > 0 ? accCards : undefined,
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
                  <div className="exec-timeline">
                    {msg.cards.map((card, j) => (
                      <ExecutionCardView key={j} card={card} />
                    ))}
                  </div>
                )}
                <div className="message-bubble markdown-content">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="message-bubble">{msg.content}</div>
            )}
          </div>
        ))}

        {streaming !== null && (
          <div className="message message-assistant">
            <div className="message-content">
              {streaming.cards.length > 0 && (
                <div className="exec-timeline">
                  {streaming.cards.map((card, j) => (
                    <ExecutionCardView key={j} card={card} active />
                  ))}
                </div>
              )}
              {streaming.answer ? (
                <div className="message-bubble markdown-content">
                  <ReactMarkdown>{streaming.answer}</ReactMarkdown>
                </div>
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

// ── 执行卡片组件 ──────────────────────────────────────────────

function ExecutionCardView({ card, active }: { card: ExecutionCard; active?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = !!card.steps?.some(s => s.thought || s.action || s.observation)
  const icon = NODE_ICONS[card.name] ?? '●'
  const timeStr = formatElapsed(card.elapsed_ms)

  return (
    <div className={`exec-card ${active ? 'exec-card-active' : ''}`}>
      <div
        className={`exec-card-header${hasDetails ? ' exec-card-clickable' : ''}`}
        onClick={() => hasDetails && setExpanded(v => !v)}
      >
        <span className="exec-icon">{icon}</span>
        <span className="exec-label">{card.label}</span>
        {card.detail && <span className="exec-detail">{card.detail}</span>}
        <span className="exec-spacer" />
        {timeStr && <span className="exec-time">{timeStr}</span>}
        {hasDetails && (
          <span className={`exec-chevron${expanded ? ' exec-chevron-open' : ''}`}>›</span>
        )}
      </div>

      {expanded && card.steps && (
        <div className="exec-card-body">
          {card.steps.map((step, i) => (
            <ReActStepView key={i} step={step} toolDetails={card.tool_details} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── ReAct 单步视图 ────────────────────────────────────────────

function ReActStepView({ step, toolDetails }: { step: ReActStep; toolDetails?: ToolDetail[] }) {
  const matchedTool = toolDetails?.find(td => td.tool_name === step.action)

  return (
    <div className="react-step">
      {step.thought && (
        <div className="step-row">
          <span className="step-tag">思考</span>
          <div className="step-box">{step.thought}</div>
        </div>
      )}

      {step.action && (
        <div className="step-row">
          <span className="step-tag">调用</span>
          <div className="step-box step-tool-box">
            <span className="tool-name">{step.action}</span>
            {matchedTool && (
              <pre className="tool-input">
                {JSON.stringify(matchedTool.input, null, 2)}
              </pre>
            )}
            {matchedTool?.elapsed_ms ? (
              <span className="tool-elapsed">{formatElapsed(matchedTool.elapsed_ms)}</span>
            ) : null}
          </div>
        </div>
      )}

      {step.observation && step.observation !== '[最终回答]' && (
        <div className="step-row">
          <span className="step-tag">结果</span>
          <div className="step-box step-observation">{step.observation}</div>
        </div>
      )}
    </div>
  )
}
