import { useState } from 'react'
import { Search, X, Zap, Bot, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api/client'
import type { RAGCandidate, RAGRerankRow, RAGDebugResponse } from '../api/client'
import '../styles/query-debugger.css'

type RAGMode = 'common' | 'agentic'

interface PipelineStep {
  id: string
  name: string
  label: string
  latencyMs: number
  details: Record<string, unknown>
}

export function QueryDebugger() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<RAGMode>('common')
  const [isQuerying, setIsQuerying] = useState(false)
  const [queryTrace, setQueryTrace] = useState<PipelineStep[]>([])
  const [traceError, setTraceError] = useState<string | null>(null)

  function clearTrace() {
    setQueryTrace([])
    setTraceError(null)
  }

  async function handleSubmit() {
    if (!query.trim() || isQuerying) return
    clearTrace()
    setIsQuerying(true)

    try {
      const result: RAGDebugResponse = await api.ragSearchDebug({ query: query.trim(), mode })

      setQueryTrace([
        {
          id: 'step-retrieve',
          name: 'recall',
          label: 'Vector Recall',
          latencyMs: Math.round(result.timings.retrieve_ms),
          details: {
            top_k: result.candidate_count,
            chunks: result.candidates,
          },
        },
        {
          id: 'step-rerank',
          name: 'rerank',
          label: 'Rerank',
          latencyMs: Math.round(result.timings.rerank_ms),
          details: { scores: result.rerank_rows },
        },
        {
          id: 'step-context',
          name: 'context_build',
          label: 'Context Build',
          latencyMs: 0,
          details: { final_chunks: result.rerank_rows.length },
        },
        {
          id: 'step-llm',
          name: 'llm_response',
          label: 'LLM Response',
          latencyMs: Math.round(result.timings.llm_ms),
          details: {
            answer: result.answer,
            total_ms: Math.round(result.timings.total_ms),
          },
        },
      ])
    } catch (e) {
      setTraceError(String(e))
    } finally {
      setIsQuerying(false)
    }
  }

  function handleClear() {
    clearTrace()
    setQuery('')
  }

  const recallStep = queryTrace.find(s => s.name === 'recall')
  const rerankStep = queryTrace.find(s => s.name === 'rerank')
  const contextStep = queryTrace.find(s => s.name === 'context_build')
  const llmStep = queryTrace.find(s => s.name === 'llm_response')

  return (
    <div className="qd-root">
      {/* Query input + mode toggle */}
      <div className="qd-toolbar">
        <div className="qd-mode-toggle">
          {(['common', 'agentic'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              disabled={isQuerying}
              className={`qd-mode-btn${mode === m ? ' active' : ''}`}
            >
              {m}
            </button>
          ))}
        </div>

        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="输入 RAG 查询..."
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          disabled={isQuerying}
          className="qd-input"
        />

        {queryTrace.length > 0 && (
          <button className="qd-icon-btn" onClick={handleClear} disabled={isQuerying}>
            <X size={14} />
          </button>
        )}

        <button
          className="qd-debug-btn"
          onClick={handleSubmit}
          disabled={!query.trim() || isQuerying}
        >
          {isQuerying ? <Loader2 size={13} className="spin" /> : <Search size={13} />}
          Debug
        </button>
      </div>

      <div className="qd-body">
        {/* Empty state */}
        {queryTrace.length === 0 && !isQuerying && !traceError && (
          <div className="qd-empty">
            输入 query 后点击 Debug，查看完整 RAG 链路
          </div>
        )}

        {/* Loading */}
        {isQuerying && (
          <div className="qd-loading">
            <Loader2 size={14} className="spin" />
            查询中…
          </div>
        )}

        {/* Error */}
        {traceError && (
          <div className="qd-error">{traceError}</div>
        )}

        {/* Pipeline steps */}
        {queryTrace.length > 0 && (
          <div className="qd-steps">
            {/* Vector Recall */}
            {recallStep?.details && (
              <Section
                title={`召回数 (${(recallStep.details.chunks as RAGCandidate[] | undefined)?.length ?? 0} chunks)`}
                latency={recallStep.latencyMs}
              >
                <div className="qd-chunks">
                  {((recallStep.details.chunks as RAGCandidate[]) ?? []).map((chunk, i) => (
                    <div key={i} className="qd-chunk">
                      <div className="qd-chunk-header">
                        <span className="qd-badge">{chunk.source.split('/').pop()}</span>
                      </div>
                      <p className="qd-chunk-preview">{chunk.preview}</p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Rerank */}
            {rerankStep?.details && (
              <Section title="精排" latency={rerankStep.latencyMs}>
                <div className="qd-rerank-list">
                  {((rerankStep.details.scores as RAGRerankRow[]) ?? []).map(s => (
                    <div key={s.rank} className="qd-rerank-row">
                      <span className="qd-badge">#{s.rank}</span>
                      <span className="qd-rerank-source">{s.source.split('/').pop()}</span>
                      <span className="qd-rerank-score">{s.score.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </Section>
            )}


            {/* LLM Response */}
            {llmStep && (
              <div className="qd-answer-card">
                <div className="qd-answer-header">
                  <Bot size={13} className="qd-bot-icon" />
                  <span className="qd-answer-label">参考答案</span>
                  <span className="qd-latency-total">
                    {(llmStep.details.total_ms as number)}ms total
                  </span>
                </div>
                <div className="qd-answer-body qd-markdown">
                  <ReactMarkdown>{llmStep.details.answer as string}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Section({
  title,
  latency,
  children,
}: {
  title: string
  latency?: number
  children: React.ReactNode
}) {
  return (
    <div className="qd-section">
      <div className="qd-section-title-row">
        <Zap size={11} className="qd-zap-icon" />
        <span className="qd-section-title">{title}</span>
        {latency !== undefined && (
          <span className="qd-section-latency">{latency}ms</span>
        )}
      </div>
      {children}
    </div>
  )
}
