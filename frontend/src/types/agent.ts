export type Artifact = {
  mime_type: string
  label: string
  data_base64: string
}

export type StockChartPoint = {
  date: string
  close: number
}

export type StockChartPayload = {
  symbol: string
  name?: string | null
  interval?: string
  points: StockChartPoint[]
}

export type TraceStep = {
  node: string
  title: string
  detail?: string
  ts?: string
}

export type RunAgentRequest = {
  query: string
  thread_id?: string | null
  model?: string | null
}

export type RunAgentResponse = {
  thread_id: string
  answer: string
  citations: string[]
  artifacts: Artifact[]
  run_trace: TraceStep[]
  pdf_base64: string | null
  plan: Record<string, unknown>
  stock_chart: StockChartPayload | null
}

export type CheckpointSummary = {
  checkpoint_id: string | null
  thread_id: string
  metadata: Record<string, unknown>
}

export type CheckpointListResponse = {
  thread_id: string
  checkpoints: CheckpointSummary[]
}

export type CheckpointStateResponse = {
  thread_id: string
  checkpoint_id: string | null
  created_at: string | null
  parent_checkpoint_id: string | null
  metadata: Record<string, unknown>
  next: string[]
  values: Record<string, unknown>
}
