import { useMemo } from 'react'
import type { RunAgentResponse } from '../types/agent'
import { StockChart } from './StockChart'

type Props = {
  result: RunAgentResponse | null
  error: string | null
  loading: boolean
  onDownloadPdf: () => void
}

const btnSecondary =
  'cursor-pointer rounded-lg border border-white/20 bg-white/5 px-3.5 py-2 font-[inherit] text-slate-100 hover:bg-white/10'

const heading = 'text-lg font-semibold text-slate-50'

export function RunOutput({ result, error, loading, onDownloadPdf }: Props) {
  const chartSrc = useMemo(() => {
    if (!result?.artifacts?.length) return null
    const img = result.artifacts.find((a) => a.mime_type === 'image/png')
    if (!img?.data_base64) return null
    return `data:image/png;base64,${img.data_base64}`
  }, [result])

  const webSearchHadNoHits = useMemo(() => {
    if (!result?.run_trace?.length) return false
    return result.run_trace.some(
      (s) =>
        s.node === 'web_search' &&
        typeof s.detail === 'string' &&
        s.detail.toLowerCase().includes('no hits'),
    )
  }, [result])

  const panelClass =
    'mt-6 rounded-xl border border-white/10 bg-[#0a1f3a]/85 p-5 text-left shadow-lg shadow-black/20 backdrop-blur-sm'

  if (loading) {
    return (
      <section className={panelClass} aria-busy="true">
        <p className="text-slate-400">Running agent…</p>
      </section>
    )
  }

  if (error) {
    return (
      <section
        className={`${panelClass} border-red-400/35 bg-red-950/20`}
        role="alert"
      >
        <h2 className={heading}>Error</h2>
        <pre className="mt-2 overflow-auto font-mono text-sm text-red-100/95">
          {error}
        </pre>
      </section>
    )
  }

  if (!result) {
    return (
      <section className={panelClass}>
        <p className="text-slate-400">
          Submit a query to see the answer and trace.
        </p>
      </section>
    )
  }

  return (
    <section className={panelClass}>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h2 className={heading}>Answer</h2>
        {result.pdf_base64 ? (
          <button type="button" className={btnSecondary} onClick={onDownloadPdf}>
            Download PDF
          </button>
        ) : null}
      </header>

      <p className="mt-2 text-sm text-slate-400">
        Thread:{' '}
        <code className="rounded bg-black/25 px-1.5 py-0.5 font-mono text-xs text-cyan-200">
          {result.thread_id}
        </code>
      </p>

      {Object.keys(result.plan ?? {}).length > 0 ? (
        <details className="my-3">
          <summary className="cursor-pointer text-sm font-medium text-cyan-300 hover:text-cyan-200">
            Plan
          </summary>
          <pre className="mt-2 overflow-auto rounded-md border border-white/10 bg-[#06162b] p-3 font-mono text-[0.78rem] text-slate-300">
            {JSON.stringify(result.plan, null, 2)}
          </pre>
        </details>
      ) : null}

      <article className="my-4 whitespace-pre-wrap text-slate-100">
        {result.answer}
      </article>

      {webSearchHadNoHits ? (
        <p
          className="my-4 rounded-lg border border-cyan-400/30 bg-cyan-950/40 p-3 text-sm text-slate-200"
          role="note"
        >
          Web search reported no hits for this run. Citations are only URLs taken from
          retrieved web or Wikipedia results; empty citations mean the answer is not tied to live
          search links.
        </p>
      ) : null}

      {result.citations?.length ? (
        <div className="mt-4">
          <h3 className={`${heading} mb-2 text-base`}>Citations</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
            {result.citations.map((c) => (
              <li key={c} className="break-all">
                {c}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {result.stock_chart?.points?.length ? (
        <div className="mt-4">
          <h3 className={`${heading} mb-2 text-base`}>Stock chart</h3>
          <div className="rounded-lg border border-cyan-400/20 bg-[#06162b]/80 p-2">
            <StockChart chart={result.stock_chart} />
          </div>
        </div>
      ) : null}

      {chartSrc ? (
        <div className="mt-4">
          <h3 className={`${heading} mb-2 text-base`}>Chart</h3>
          <img
            src={chartSrc}
            alt="Generated chart"
            className="h-auto max-w-full rounded-lg border border-white/10"
          />
        </div>
      ) : null}

      {result.run_trace?.length ? (
        <details className="mt-4 rounded-lg border border-white/10 bg-[#06162b]/50">
          <summary className="cursor-pointer px-3 py-3 text-sm font-medium text-cyan-300 hover:bg-white/5 hover:text-cyan-200">
            <span className="inline-flex items-center gap-2">
              <span className="text-base font-semibold text-slate-50">Run trace</span>
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-normal text-slate-400">
                {result.run_trace.length} steps · click to expand
              </span>
            </span>
          </summary>
          <div className="border-t border-white/10 px-3 pb-3 pt-2">
            <p className="mb-3 text-xs text-slate-500">
              Technical log of planner, retrieval, synthesis, and verification.
            </p>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-300">
              {result.run_trace.map((step, i) => (
                <li key={`${step.node}-${i}`}>
                  <strong className="text-slate-100">{step.node}</strong>
                  {step.title ? `: ${step.title}` : null}
                  {step.detail ? (
                    <div className="mt-1 text-[0.88rem] text-slate-400">{step.detail}</div>
                  ) : null}
                </li>
              ))}
            </ol>
          </div>
        </details>
      ) : null}
    </section>
  )
}
