const API_BASE = '/api'

export interface RAGSearchRequest {
  query: string
  mode: 'agentic' | 'common'
}

export interface RAGSearchResponse {
  answer: string
}

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  created_at: string
  documents_count?: number
}

export interface RAGDocument {
  id: number
  name: string
  file_path: string
  status: string
  created_at: string
  content?: string
}

export const api = {
  // RAG 搜索
  async ragSearch(req: RAGSearchRequest): Promise<string> {
    const res = await fetch(`${API_BASE}/rag_search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) throw new Error(`请求失败 (HTTP ${res.status})`)
    const data = await res.json()
    return data.answer
  },

  // 知识库 CRUD
  async createKnowledgeBase(name: string, description: string = ''): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/create_knowledge_base`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    })
    if (!res.ok) throw new Error(`创建知识库失败 (HTTP ${res.status})`)
    const data = await res.json()
    return data.answer
  },

  async listKnowledgeBases(skip: number = 0, limit: number = 10): Promise<KnowledgeBase[]> {
    const res = await fetch(`${API_BASE}/list_knowledge_bases?skip=${skip}&limit=${limit}`)
    if (!res.ok) throw new Error(`获取知识库列表失败`)
    const data = await res.json()
    return data.answer
  },

  async getKnowledgeBase(id: number): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/get_knowledge_base?id=${id}`)
    if (!res.ok) throw new Error(`获取知识库失败`)
    const data = await res.json()
    return data.answer
  },

  async updateKnowledgeBase(id: number, name: string, description: string = ''): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/update_knowledge_base`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, name, description }),
    })
    if (!res.ok) throw new Error(`更新知识库失败`)
    const data = await res.json()
    return data.answer
  },

  async deleteKnowledgeBase(id: number): Promise<{ id: number; message: string }> {
    const res = await fetch(`${API_BASE}/delete_knowledge_base`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    })
    if (!res.ok) throw new Error(`删除知识库失败`)
    const data = await res.json()
    return data.answer
  },

  // 文档 CRUD
  async uploadDocument(
    kbId: number,
    name: string,
    filePath: string,
    content: string
  ): Promise<RAGDocument> {
    const res = await fetch(`${API_BASE}/upload_knowledge_base_document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        knowledge_base_id: kbId,
        name,
        file_path: filePath,
        document: content,
      }),
    })
    if (!res.ok) throw new Error(`上传文档失败`)
    const data = await res.json()
    return data.answer
  },

  async listDocuments(kbId: number, skip: number = 0, limit: number = 10): Promise<RAGDocument[]> {
    const res = await fetch(`${API_BASE}/list_knowledge_base_documents?knowledge_base_id=${kbId}&skip=${skip}&limit=${limit}`)
    if (!res.ok) throw new Error(`获取文档列表失败`)
    const data = await res.json()
    return data.answer
  },

  async getDocument(kbId: number, docId: number): Promise<RAGDocument> {
    const res = await fetch(`${API_BASE}/get_knowledge_base_document?knowledge_base_id=${kbId}&document_id=${docId}`)
    if (!res.ok) throw new Error(`获取文档失败`)
    const data = await res.json()
    return data.answer
  },

  async deleteDocument(kbId: number, docId: number): Promise<{ id: number; message: string }> {
    const res = await fetch(`${API_BASE}/delete_knowledge_base_document`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        knowledge_base_id: kbId,
        document_id: docId,
      }),
    })
    if (!res.ok) throw new Error(`删除文档失败`)
    const data = await res.json()
    return data.answer
  },
}
