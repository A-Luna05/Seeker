import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { StockChartPayload } from '../types/agent'

type Props = {
  chart: StockChartPayload
}

const tooltipStyles = {
  backgroundColor: '#06162b',
  border: '1px solid rgba(34, 211, 238, 0.35)',
  borderRadius: 8,
  color: '#e2e8f0',
}

export function StockChart({ chart }: Props) {
  const points = chart.points ?? []
  const data = useMemo(
    () => points.map((p) => ({ date: p.date, close: p.close })),
    [points],
  )

  if (data.length < 2) {
    return (
      <p className="text-sm text-slate-400">
        Not enough data points to draw a chart for {chart.symbol}.
      </p>
    )
  }

  const title = [chart.name, chart.symbol].filter(Boolean).join(' · ')
  const sub = `${chart.interval ?? 'daily'} closes · ${points.length} sessions`
  const last = points[points.length - 1]

  return (
    <div className="w-full">
      <div className="mb-3 px-1">
        <p className="text-sm font-semibold text-slate-100">{title}</p>
        <p className="text-xs text-slate-400">{sub}</p>
        {last ? (
          <p className="mt-1 text-xs text-cyan-200/90">
            Last close: {last.date} · ${last.close.toFixed(2)}
          </p>
        ) : null}
      </div>
      <div className="h-[280px] w-full min-w-0" aria-label={`Stock chart for ${chart.symbol}`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.18)" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.12)' }}
              minTickGap={36}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.12)' }}
              tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
              width={52}
            />
            <Tooltip
              contentStyle={tooltipStyles}
              labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Close']}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#22d3ee', stroke: '#0a1f3a', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
