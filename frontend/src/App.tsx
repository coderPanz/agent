import { useState } from 'react'
import { ChatPage } from './pages/Chat'
import { KnowledgeBaseManager } from './pages/KnowledgeBaseManager'
import './App.css'

type Page = 'chat' | 'rag'

interface ChatRecord {
  id: string
  title: string
}

export default function App() {
  const [page, setPage] = useState<Page>('chat')
  const [historyOpen, setHistoryOpen] = useState(true)
  const [chatHistory, setChatHistory] = useState<ChatRecord[]>([])
  const [chatKey, setChatKey] = useState(0)

  function startNewChat() {
    setPage('chat')
    setChatKey(k => k + 1)
  }

  function addToHistory(title: string) {
    setChatHistory(prev => [
      { id: Date.now().toString(), title },
      ...prev.slice(0, 19),
    ])
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <nav className="sidebar-nav">
          <button
            className={`sidebar-item${page === 'chat' ? ' active' : ''}`}
            onClick={startNewChat}
          >
            <IconEdit />
            新对话
          </button>
          <button
            className={`sidebar-item${page === 'rag' ? ' active' : ''}`}
            onClick={() => setPage('rag')}
          >
            <IconDatabase />
            RAG 系统
          </button>
        </nav>

        <div className="sidebar-divider" />

        <div className="sidebar-section">
          <button
            className={`sidebar-section-title${historyOpen ? ' open' : ''}`}
            onClick={() => setHistoryOpen(o => !o)}
          >
            <span>历史对话</span>
            <IconChevron />
          </button>
          {historyOpen && (
            <div className="history-list">
              {chatHistory.length === 0 ? (
                <div className="history-empty">暂无记录</div>
              ) : (
                chatHistory.map(h => (
                  <button key={h.id} className="history-item" onClick={startNewChat}>
                    {h.title}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="sidebar-bottom">
          <button className="sidebar-item">
            <IconSettings />
            设置
          </button>
        </div>
      </aside>

      <main className="main-content">
        {page === 'chat' ? (
          <ChatPage key={chatKey} onFirstMessage={addToHistory} />
        ) : (
          <KnowledgeBaseManager />
        )}
      </main>
    </div>
  )
}

function IconEdit() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

function IconDatabase() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  )
}

function IconChevron() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function IconSettings() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  )
}
