import { useState, useEffect } from 'react'
import { api, KnowledgeBase, RAGDocument } from '../api/client'
import '../styles/knowledge-base.css'

export function KnowledgeBaseManager() {
  const [bases, setBases] = useState<KnowledgeBase[]>([])
  const [selectedBase, setSelectedBase] = useState<KnowledgeBase | null>(null)
  const [documents, setDocuments] = useState<RAGDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showUploadForm, setShowUploadForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  useEffect(() => {
    loadBases()
  }, [])

  useEffect(() => {
    if (selectedBase) {
      loadDocuments(selectedBase.id)
    } else {
      setDocuments([])
    }
  }, [selectedBase])

  async function loadBases() {
    setLoading(true)
    setError(null)
    try {
      const list = await api.listKnowledgeBases()
      setBases(list)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载知识库失败')
    } finally {
      setLoading(false)
    }
  }

  async function loadDocuments(kbId: number) {
    try {
      const list = await api.listDocuments(kbId)
      setDocuments(list)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载文档失败')
    }
  }

  async function handleCreateBase() {
    if (!newName.trim()) return
    setLoading(true)
    try {
      const base = await api.createKnowledgeBase(newName, newDescription)
      setBases([...bases, base])
      setNewName('')
      setNewDescription('')
      setShowCreateForm(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建知识库失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpdateBase(id: number) {
    setLoading(true)
    try {
      const updated = await api.updateKnowledgeBase(id, newName, newDescription)
      setBases(bases.map(b => b.id === id ? updated : b))
      if (selectedBase?.id === id) {
        setSelectedBase(updated)
      }
      setNewName('')
      setNewDescription('')
      setEditingId(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新知识库失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteBase(id: number) {
    if (!confirm('确认删除该知识库？')) return
    setLoading(true)
    try {
      await api.deleteKnowledgeBase(id)
      setBases(bases.filter(b => b.id !== id))
      if (selectedBase?.id === id) {
        setSelectedBase(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除知识库失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteDocument(docId: number) {
    if (!selectedBase || !confirm('确认删除该文档？')) return
    try {
      await api.deleteDocument(selectedBase.id, docId)
      setDocuments(documents.filter(d => d.id !== docId))
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除文档失败')
    }
  }

  return (
    <div className="kb-manager">
      <div className="kb-layout">
        {/* 左侧：知识库列表 */}
        <div className="kb-sidebar">
          <div className="kb-sidebar-header">
            <h2>知识库</h2>
            <button
              className="btn-primary btn-sm"
              onClick={() => setShowCreateForm(true)}
              disabled={loading}
            >
              + 新建
            </button>
          </div>

          <div className="kb-list">
            {bases.map(base => (
              <div
                key={base.id}
                className={`kb-item${selectedBase?.id === base.id ? ' active' : ''}`}
                onClick={() => setSelectedBase(base)}
              >
                <div className="kb-item-title">{base.name}</div>
                <div className="kb-item-meta">
                  {base.documents_count ?? 0} 文档
                </div>
              </div>
            ))}
            {bases.length === 0 && !loading && (
              <div className="kb-empty">暂无知识库</div>
            )}
          </div>
        </div>

        {/* 右侧：详情和文档 */}
        <div className="kb-content">
          {selectedBase ? (
            <>
              <div className="kb-header">
                <div>
                  <h2>{selectedBase.name}</h2>
                  <p className="kb-description">{selectedBase.description}</p>
                </div>
                <div className="kb-actions">
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() => {
                      setNewName(selectedBase.name)
                      setNewDescription(selectedBase.description)
                      setEditingId(selectedBase.id)
                    }}
                  >
                    编辑
                  </button>
                  <button
                    className="btn-danger btn-sm"
                    onClick={() => handleDeleteBase(selectedBase.id)}
                  >
                    删除
                  </button>
                </div>
              </div>

              <div className="documents-section">
                <div className="documents-header">
                  <h3>文档列表</h3>
                  <button
                    className="btn-primary btn-sm"
                    onClick={() => setShowUploadForm(true)}
                    disabled={loading}
                  >
                    + 上传
                  </button>
                </div>

                <div className="documents-list">
                  {documents.map(doc => (
                    <div key={doc.id} className="document-item">
                      <div className="document-info">
                        <div className="document-name">{doc.name}</div>
                        <div className="document-meta">
                          <span className="status">{doc.status}</span>
                          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <button
                        className="btn-danger btn-xs"
                        onClick={() => handleDeleteDocument(doc.id)}
                      >
                        删除
                      </button>
                    </div>
                  ))}
                  {documents.length === 0 && (
                    <div className="documents-empty">暂无文档</div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="kb-empty-state">
              <p>选择或创建一个知识库开始</p>
            </div>
          )}
        </div>
      </div>

      {/* 创建/编辑知识库模态框 */}
      {(showCreateForm || editingId) && (
        <div className="modal-overlay" onClick={() => {
          setShowCreateForm(false)
          setEditingId(null)
          setNewName('')
          setNewDescription('')
        }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editingId ? '编辑知识库' : '新建知识库'}</h3>
            <input
              type="text"
              className="form-input"
              placeholder="知识库名称"
              value={newName}
              onChange={e => setNewName(e.target.value)}
            />
            <textarea
              className="form-input"
              placeholder="描述（可选）"
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              rows={3}
            />
            <div className="modal-actions">
              <button
                className="btn-primary"
                onClick={() => {
                  if (editingId) {
                    handleUpdateBase(editingId)
                  } else {
                    handleCreateBase()
                  }
                }}
                disabled={loading || !newName.trim()}
              >
                {editingId ? '更新' : '创建'}
              </button>
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowCreateForm(false)
                  setEditingId(null)
                  setNewName('')
                  setNewDescription('')
                }}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 上传文档模态框 */}
      {showUploadForm && selectedBase && (
        <UploadDocumentModal
          kbId={selectedBase.id}
          onClose={() => setShowUploadForm(false)}
          onSuccess={() => {
            setShowUploadForm(false)
            loadDocuments(selectedBase.id)
          }}
        />
      )}

      {error && <div className="error-banner">{error}</div>}
    </div>
  )
}

function UploadDocumentModal({
  kbId,
  onClose,
  onSuccess,
}: {
  kbId: number
  onClose: () => void
  onSuccess: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [docName, setDocName] = useState('')
  const [docPath, setDocPath] = useState('')
  const [docContent, setDocContent] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleUpload() {
    if (!docName.trim() || !docPath.trim() || !docContent.trim()) {
      setError('请填写所有字段')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await api.uploadDocument(kbId, docName, docPath, docContent)
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
        <input
          type="text"
          className="form-input"
          placeholder="文档名称"
          value={docName}
          onChange={e => setDocName(e.target.value)}
        />
        <input
          type="text"
          className="form-input"
          placeholder="文件路径"
          value={docPath}
          onChange={e => setDocPath(e.target.value)}
        />
        <textarea
          className="form-input"
          placeholder="文档内容"
          value={docContent}
          onChange={e => setDocContent(e.target.value)}
          rows={8}
        />
        {error && <div className="form-error">{error}</div>}
        <div className="modal-actions">
          <button
            className="btn-primary"
            onClick={handleUpload}
            disabled={loading || !docName.trim()}
          >
            上传
          </button>
          <button className="btn-secondary" onClick={onClose}>
            取消
          </button>
        </div>
      </div>
    </div>
  )
}
