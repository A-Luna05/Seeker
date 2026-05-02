import { useState } from 'react'
import { getCheckpointState, getThreadLatestState, listCheckpoints } from '../api/client'
import type { CheckpointStateResponse, CheckpointSummary } from '../types/agent'

type Props = {
  threadId: string | null
}

const btn =
  'cursor-pointer rounded-lg border border-white/20 bg-cyan-500/20 px-3.5 py-2 text-sm font-[inherit] text-slate-100 hover:bg-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50'

const heading = 'text-lg font-semibold text-slate-50'

export function CheckpointList({ threadId }: Props) {
  const [items, setItems] = useState<CheckpointSummary[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fullState, setFullState] = useState<CheckpointStateResponse | null>(null)
  const [stateLoading, setStateLoading] = useState(false)
  const [stateError, setStateError] = useState<string | null>(null)

  async function load() {
    if (!threadId) return
    setLoading(true)
    setError(null)
    try {
      const data = await listCheckpoints(threadId)
      setItems(data.checkpoints)
    } catch (e) {
      setItems(null)
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  async function loadLatestState() {
    if (!threadId) return
    setStateLoading(true)
    setStateError(null)
    try {
      const s = await getThreadLatestState(threadId)
      setFullState(s)
    } catch (e) {
      setFullState(null)
      setStateError(e instanceof Error ? e.message : String(e))
    } finally {
      setStateLoading(false)
    }
  }

  async function loadStateAt(checkpointId: string) {
    if (!threadId) return
    setStateLoading(true)
    setStateError(null)
    try {
      const s = await getCheckpointState(threadId, checkpointId)
      setFullState(s)
    } catch (e) {
      setFullState(null)
      setStateError(e instanceof Error ? e.message : String(e))
    } finally {
      setStateLoading(false)
    }
  }

  const panelClass =
    'mt-6 rounded-xl border border-white/10 bg-[#0a1f3a]/85 p-5 text-left shadow-lg shadow-black/20 backdrop-blur-sm'

  const traceLen =
    fullState?.values?.run_trace != null && Array.isArray(fullState.values.run_trace)
      ? fullState.values.run_trace.length
      : null

  if (!threadId) {
    return (
      <section className={panelClass}>
        <p className="text-slate-400">
          Run a query to get a thread id, then load checkpoints.
        </p>
      </section>
    )
  }

  return (
    <section className={panelClass}>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h2 className={heading}>Checkpoints</h2>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btn} onClick={load} disabled={loading}>
            {loading ? 'Loading…' : 'Load from DB'}
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => void loadLatestState()}
            disabled={stateLoading}
          >
            {stateLoading ? 'Loading…' : 'Latest full state'}
          </button>
        </div>
      </header>
      <p className="mt-3 text-xs leading-relaxed text-slate-500">
        The list below shows LangGraph <strong className="text-slate-400">metadata</strong> only
        (step, source, model). The full graph (
        <code className="text-cyan-300/90">run_trace</code>,{' '}
        <code className="text-cyan-300/90">messages</code>,{' '}
        <code className="text-cyan-300/90">web_results</code>, etc.) lives in the checkpoint
        payload — use <strong className="text-slate-400">Latest full state</strong> or{' '}
        <strong className="text-slate-400">State</strong> on each row.
      </p>
      {error ? (
        <p className="mt-2 text-sm text-red-300" role="alert">
          {error}
        </p>
      ) : null}
      {stateError ? (
        <p className="mt-2 text-sm text-red-300" role="alert">
          {stateError}
        </p>
      ) : null}
      {!items?.length && !error && !loading ? (
        <p className="mt-2 text-slate-400">No checkpoints loaded yet.</p>
      ) : null}
      {fullState ? (
        <div className="mt-4 rounded-lg border border-cyan-500/25 bg-[#06162b]/80 p-3">
          <p className="mb-2 text-xs text-slate-400">
            Checkpoint <code className="text-cyan-200">{fullState.checkpoint_id ?? '—'}</code>
            {traceLen != null ? (
              <>
                {' '}
                · <span className="text-slate-300">{traceLen}</span> trace steps in{' '}
                <code className="text-cyan-200">values</code>
              </>
            ) : null}
          </p>
          <pre className="max-h-[min(420px,50svh)] overflow-auto rounded-md border border-white/10 bg-[#06162b] p-2 font-mono text-[0.65rem] leading-snug text-slate-400">
            {JSON.stringify(fullState, null, 2)}
          </pre>
        </div>
      ) : null}
      {items && items.length > 0 ? (
        <ul className="mt-3 list-none space-y-3 p-0">
          {items.map((c, i) => (
            <li key={`${c.checkpoint_id ?? i}`} className="rounded-lg border border-white/5 p-2">
              <div className="flex flex-wrap items-center gap-2">
                <code className="rounded bg-black/25 px-1.5 py-0.5 font-mono text-xs text-cyan-200">
                  {c.checkpoint_id ?? '(no id)'}
                </code>
                {c.checkpoint_id ? (
                  <button
                    type="button"
                    className={`${btn} !py-1.5 text-xs`}
                    disabled={stateLoading}
                    onClick={() => void loadStateAt(c.checkpoint_id!)}
                  >
                    State
                  </button>
                ) : null}
              </div>
              <pre className="mt-1.5 overflow-auto rounded-md border border-white/10 bg-[#06162b] p-2 font-mono text-[0.72rem] text-slate-400">
                {JSON.stringify(c.metadata, null, 2)}
              </pre>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
