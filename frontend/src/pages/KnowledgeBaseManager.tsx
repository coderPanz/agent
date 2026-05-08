import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { KnowledgeBase, RAGDocument, RAGDebugResponse } from '../api/client'
import '../styles/knowledge-base.css'

type Tab = 'knowledge-base' | 'query-debugger' | 'pipeline-trace'

interface ConfirmDialog {
  message: string
  onConfirm: () => void
}

export function KnowledgeBaseManager() {
  const [tab, setTab] = useState<Tab>('knowledge-base')
  const [bases, setBases] = useState<KnowledgeBase[]>([])
  const [selected, setSelected] = useState<KnowledgeBase | null>(null)
  const [documents, setDocuments] = useState<RAGDocument[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<ConfirmDialog | null>(null)

  const [debugQuery, setDebugQuery] = useState('')
  const [debugMode, setDebugMode] = useState<'agentic' | 'common'>('agentic')
  const [debugResult, setDebugResult] = useState<RAGDebugResponse | null>(null)
  const [debugLoading, setDebugLoading] = useState(false)
  const [debugError, setDebugError] = useState<string | null>(null)

  useEffect(() => { loadBases() }, [])

  useEffect(() => {
    if (selected) loadDocuments(selected.id)
    else setDocuments([])
  }, [selected])

  async function loadBases() {
    setLoading(true)
    try {
      setBases(await api.listKnowledgeBases())
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  async function loadDocuments(kbId: number) {
    try {
      setDocuments(await api.listDocuments(kbId))
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载文档失败')
    }
  }

  async function handleCreate() {
    if (!formName.trim()) return
    setLoading(true)
    try {
      const kb = await api.createKnowledgeBase(formName, formDesc)
      setBases(prev => [...prev, kb])
      closeForm()
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpdate(id: number) {
    setLoading(true)
    try {
      const updated = await api.updateKnowledgeBase(id, formName, formDesc)
      setBases(prev => prev.map(b => b.id === id ? updated : b))
      if (selected?.id === id) setSelected(updated)
      closeForm()
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteBase(id: number) {
    setConfirm({
      message: '确认删除该知识库及其所有文档？',
      onConfirm: async () => {
        setLoading(true)
        try {
          await api.deleteKnowledgeBase(id)
          setBases(prev => prev.filter(b => b.id !== id))
          if (selected?.id === id) setSelected(null)
          setConfirm(null)
        } catch (e) {
          setError(e instanceof Error ? e.message : '删除失败')
        } finally {
          setLoading(false)
        }
      }
    })
  }

  async function handleDeleteDoc(docId: number) {
    if (!selected) return
    setConfirm({
      message: '确认删除该文档？',
      onConfirm: async () => {
        try {
          await api.deleteDocument(selected.id, docId)
          setDocuments(prev => prev.filter(d => d.id !== docId))
          setConfirm(null)
        } catch (e) {
          setError(e instanceof Error ? e.message : '删除文档失败')
        }
      }
    })
  }

  function openCreate() {
    setFormName('')
    setFormDesc('')
    setEditingId(null)
    setShowCreate(true)
  }

  function openEdit(kb: KnowledgeBase) {
    setFormName(kb.name)
    setFormDesc(kb.description)
    setEditingId(kb.id)
    setShowCreate(true)
  }

  function closeForm() {
    setShowCreate(false)
    setEditingId(null)
    setFormName('')
    setFormDesc('')
  }

  async function handleDebugQuery() {
    if (!debugQuery.trim() || debugLoading) return
    setDebugLoading(true)
    setDebugError(null)
    try {
      const result = await api.ragSearchDebug({ query: debugQuery.trim(), mode: debugMode })
      setDebugResult(result)
    } catch (e) {
      setDebugError(e instanceof Error ? e.message : '调试查询失败')
    } finally {
      setDebugLoading(false)
    }
  }

  function clearDebugResult() {
    setDebugResult(null)
    setDebugQuery('')
    setDebugError(null)
  }

  return (
    <div className="rag-studio">
      {/* Tab bar */}
      <div className="rag-tab-bar">
        <button
          className={`rag-tab${tab === 'knowledge-base' ? ' active' : ''}`}
          onClick={() => setTab('knowledge-base')}
        >
          <IconKB />
          知识库
        </button>
        <button
          className={`rag-tab${tab === 'query-debugger' ? ' active' : ''}`}
          onClick={() => setTab('query-debugger')}
        >
          <IconSearch />
          RAG查询调试器
        </button>
        <button
          className={`rag-tab${tab === 'pipeline-trace' ? ' active' : ''}`}
          onClick={() => setTab('pipeline-trace')}
        >
          <IconPipeline />
          管道追踪
        </button>
      </div>

      {tab === 'knowledge-base' && (
        <div className="kb-body">
          {/* Left: KB list */}
          <div className="kb-list-panel">
            <div className="kb-list-header">
              <span>知识库</span>
              <button className="kb-new-btn" onClick={openCreate} disabled={loading}>
                + New
              </button>
            </div>
            <div className="kb-list-items">
              {bases.length === 0 && !loading && (
                <div className="kb-empty">暂无知识库</div>
              )}
              {bases.map(base => (
                <div
                  key={base.id}
                  className={`kb-card${selected?.id === base.id ? ' active' : ''}`}
                  onClick={() => setSelected(base)}
                >
                  <div className="kb-card-name">{base.name}</div>
                  <div className="kb-card-meta">
                    {base.documents_count ?? 0} docs
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Detail */}
          {selected ? (
            <div className="kb-detail">
              <div className="kb-detail-header">
                <div>
                  <div className="kb-detail-title">{selected.name}</div>
                  <div className="kb-embedding">
                    Embedding: BAAI/bge-large-zh-v1.5
                    {selected.description && ` · ${selected.description}`}
                  </div>
                </div>
                <div className="kb-header-actions">
                  <button className="btn-outline" onClick={() => openEdit(selected)}>
                    编辑
                  </button>
                  <button className="btn-outline" onClick={() => loadDocuments(selected.id)}>
                    <IconRefresh /> &nbsp;刷新
                  </button>
                  <button className="btn-primary" onClick={() => setShowUpload(true)}>
                    ↑ Upload
                  </button>
                  <button className="btn-danger" onClick={() => handleDeleteBase(selected.id)}>
                    删除
                  </button>
                </div>
              </div>

              <div className="doc-list">
                {documents.length === 0 ? (
                  <div className="doc-empty">暂无文档，点击 Upload 上传</div>
                ) : (
                  documents.map(doc => (
                    <div key={doc.id} className="doc-row">
                      <IconFile />
                      <div className="doc-info">
                        <div className="doc-name">{doc.name}</div>
                        <div className="doc-meta">{doc.file_path}</div>
                      </div>
                      <span className={`doc-status ${doc.status}`}>{doc.status}</span>
                      <div className="doc-row-actions">
                        <button
                          className="doc-action-btn danger"
                          onClick={() => handleDeleteDoc(doc.id)}
                          title="删除"
                        >
                          <IconTrash />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="kb-empty-state">选择或创建一个知识库</div>
          )}
        </div>
      )}

      {tab === 'query-debugger' && (
        <div className="debugger-container">
          <div className="debugger-header">
            <div className="debugger-input-group">
              <div className="mode-toggle">
                <button
                  className={`toggle-btn${debugMode === 'agentic' ? ' active' : ''}`}
                  onClick={() => setDebugMode('agentic')}
                  disabled={debugLoading}
                >
                  Agentic
                </button>
                <button
                  className={`toggle-btn${debugMode === 'common' ? ' active' : ''}`}
                  onClick={() => setDebugMode('common')}
                  disabled={debugLoading}
                >
                  Common
                </button>
              </div>
              <input
                type="text"
                className="debugger-input"
                placeholder="输入查询文本..."
                value={debugQuery}
                onChange={e => setDebugQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleDebugQuery()}
                disabled={debugLoading}
              />
              <button
                className="btn-primary"
                onClick={handleDebugQuery}
                disabled={!debugQuery.trim() || debugLoading}
              >
                {debugLoading ? '调试中...' : '调试'}
              </button>
              {debugResult && (
                <button className="btn-outline" onClick={clearDebugResult} disabled={debugLoading}>
                  清空
                </button>
              )}
            </div>
          </div>

          <div className="debugger-body">
            {!debugResult && !debugError && (
              <div className="debugger-empty">
                输入查询文本并点击"调试"来查看 RAG 完整链路
              </div>
            )}

            {debugError && (
              <div className="debugger-error">
                {debugError}
              </div>
            )}

            {debugResult && (
              <div className="debugger-result">
                {/* Query Info */}
                <div className="debug-section">
                  <div className="debug-section-title">查询信息</div>
                  <div className="debug-info">
                    <div className="info-row">
                      <span className="info-label">模式:</span>
                      <span className="info-value">{debugResult.mode}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-label">总耗时:</span>
                      <span className="info-value">{debugResult.timings.total_ms}ms</span>
                    </div>
                  </div>
                </div>

                {/* Recall Info */}
                <div className="debug-section">
                  <div className="debug-section-title">向量召回</div>
                  <div className="debug-info">
                    <div className="info-row">
                      <span className="info-label">召回数量:</span>
                      <span className="info-value">{debugResult.candidate_count}</span>
                    </div>
                  </div>
                </div>

                {/* Rerank Info */}
                {debugResult.rerank_rows && debugResult.rerank_rows.length > 0 && (
                  <div className="debug-section">
                    <div className="debug-section-title">重排结果</div>
                    <div className="debug-rerank-list">
                      {(debugResult.rerank_rows as Array<{ rank?: number; score?: number }>).map((row, i) => (
                        <div key={i} className="rerank-item">
                          <span>#{row.rank ?? i + 1}</span>
                          <span className="score">{(row.score ?? 0).toFixed(4)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Answer */}
                <div className="debug-section">
                  <div className="debug-section-title">LLM 回答</div>
                  <div className="debug-answer">{debugResult.answer}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'pipeline-trace' && (
        <div className="tab-placeholder">Pipeline Trace — 即将推出</div>
      )}

      {/* Create / Edit modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={closeForm}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editingId ? '编辑知识库' : '新建知识库'}</h3>
            <input
              className="form-input"
              placeholder="知识库名称"
              value={formName}
              onChange={e => setFormName(e.target.value)}
            />
            <textarea
              className="form-input"
              placeholder="描述（可选）"
              value={formDesc}
              onChange={e => setFormDesc(e.target.value)}
              rows={3}
            />
            <div className="modal-actions">
              <button
                className="btn-primary"
                onClick={() => editingId ? handleUpdate(editingId) : handleCreate()}
                disabled={loading || !formName.trim()}
              >
                {editingId ? '保存' : '创建'}
              </button>
              <button className="btn-outline" onClick={closeForm}>取消</button>
            </div>
          </div>
        </div>
      )}

      {/* Upload modal */}
      {showUpload && selected && (
        <UploadModal
          kbId={selected.id}
          onClose={() => setShowUpload(false)}
          onSuccess={() => { setShowUpload(false); loadDocuments(selected.id) }}
        />
      )}

      {confirm && (
        <div className="modal-overlay" onClick={() => setConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>确认</h3>
            <p style={{ color: 'var(--text)', marginBottom: '24px' }}>{confirm.message}</p>
            <div className="modal-actions">
              <button className="btn-danger" onClick={confirm.onConfirm} disabled={loading}>
                删除
              </button>
              <button className="btn-outline" onClick={() => setConfirm(null)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}
    </div>
  )
}

function UploadModal({
  kbId, onClose, onSuccess,
}: {
  kbId: number
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload() {
    if (!name.trim() || !path.trim() || !content.trim()) {
      setError('请填写所有字段')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await api.uploadDocument(kbId, name, path, content)
      onSuccess()
    } catch (e) {
      setError(e instanceof Error ? e.message : '上传失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
        <h3>上传文档</h3>
        <input className="form-input" placeholder="文档名称" value={name} onChange={e => setName(e.target.value)} />
        <input className="form-input" placeholder="文件路径" value={path} onChange={e => setPath(e.target.value)} />
        <textarea className="form-input" placeholder="文档内容" value={content} onChange={e => setContent(e.target.value)} rows={8} />
        {error && <div className="form-error">{error}</div>}
        <div className="modal-actions">
          <button className="btn-primary" onClick={handleUpload} disabled={loading || !name.trim()}>上传</button>
          <button className="btn-outline" onClick={onClose}>取消</button>
        </div>
      </div>
    </div>
  )
}

/* ── Icons ── */
function IconKB() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    </svg>
  )
}

function IconSearch() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function IconPipeline() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}

function IconFile() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

function IconTrash() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  )
}

function IconRefresh() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline', width: 13, height: 13 }}>
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
    </svg>
  )
}
