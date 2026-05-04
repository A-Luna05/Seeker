import { useCallback, useState, type FormEvent } from 'react'
import { Loader2, Play } from 'lucide-react'
import { runAgent } from '../api/client'
import type { RunAgentResponse } from '../types/agent'
import { CheckpointList } from './CheckpointList'
import { RunOutput } from './RunOutput'

function downloadPdfBase64(base64: string, filename: string) {
  const bin = atob(base64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  const blob = new Blob([bytes], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const MODEL_OPTIONS = [
  { label: 'GPT 4.1 mini', value: 'gpt-4.1-mini' },
  { label: 'GPT 5.4 mini', value: 'gpt-5.4-mini' },
] as const

/** Inputs: slightly lifted from page bg, not solid black */
const inputClass =
  'rounded-lg border border-white/15 bg-[#0d2847] px-3 py-2.5 font-[inherit] text-slate-100 shadow-inner shadow-black/20 placeholder:text-slate-500 focus:border-cyan-400/55 focus:outline-none focus:ring-2 focus:ring-cyan-500/25'

const selectClass = `${inputClass} cursor-pointer pr-10`

const btnBase =
  'cursor-pointer rounded-lg border px-4 py-2.5 font-[inherit] disabled:cursor-not-allowed disabled:opacity-50'

export function SearchAgentPanel() {
  const [query, setQuery] = useState('')
  const [model, setModel] = useState<string>(MODEL_OPTIONS[0].value)
  const [result, setResult] = useState<RunAgentResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      setLoading(true)
      setError(null)
      try {
        const data = await runAgent({
          query: query.trim(),
          model,
          thread_id: result?.thread_id ?? null,
        })
        setResult(data)
      } catch (err) {
        setResult(null)
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    },
    [query, model, result],
  )

  const onDownloadPdf = useCallback(() => {
    if (!result?.pdf_base64 || !result.thread_id) return
    downloadPdfBase64(result.pdf_base64, `search-agent-${result.thread_id}.pdf`)
  }, [result])

  return (
    <div className="mx-auto max-w-2xl px-5 py-8 pb-16 text-left">
      <header>
        <h1 className="mb-1.5 py-4  text-2xl font-bold tracking-tight text-slate-50">
          Seeker - LangGraph Search Agent
        </h1>
        <p className="m-0 text-sm text-slate-400">
          LangGraph · DuckDuckGo · Brave · Wikipedia · Alpha Vantage · Charting · PDF Reports
        </p>
      </header>

      <form className="mt-6 flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="flex max-w-md flex-col gap-1.5 text-slate-200">
          <span className="text-sm font-medium text-slate-200">Model</span>
          <select
            className={selectClass}
            value={model}
            onChange={(e) => setModel(e.target.value)}
            aria-label="Model"
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-slate-200">
          <span className="text-sm font-medium text-slate-200">Query</span>
          <textarea
            className={`${inputClass} min-h-[6.5rem] resize-y`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            placeholder="What do you want to know about? Example: What is NVIDIA, and what have they done recently?"
            required
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            className={`${btnBase} inline-flex items-center justify-center gap-2 border border-cyan-700/50 bg-cyan-800 text-white shadow-sm shadow-black/25 hover:bg-cyan-700 hover:border-cyan-600/45`}
            disabled={loading || !query.trim()}
            aria-busy={loading}
          >
            {loading ? (
              <>
                <Loader2 className="size-4 shrink-0 animate-spin" strokeWidth={2.25} aria-hidden />
                Running…
              </>
            ) : (
              <>
                <Play className="size-4 shrink-0 opacity-95" aria-hidden />
                Run
              </>
            )}
          </button>
          <button
            type="button"
            className={`${btnBase} border-white/20 bg-white/5 text-slate-100 hover:bg-white/10`}
            onClick={() => {
              setResult(null)
              setError(null)
            }}
          >
            New thread
          </button>
        </div>
      </form>

      <RunOutput
        result={result}
        error={error}
        loading={loading}
        onDownloadPdf={onDownloadPdf}
      />

      <CheckpointList threadId={result?.thread_id ?? null} />
    </div>
  )
}
