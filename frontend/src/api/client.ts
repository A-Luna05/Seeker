import type {
  CheckpointListResponse,
  CheckpointStateResponse,
  RunAgentRequest,
  RunAgentResponse,
} from '../types/agent'

const base = () =>
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''

/** Fire-and-forget warmup for hosts that sleep (e.g. Render). Errors are ignored. */
export function pingHealth(): void {
  void fetch(`${base()}/health`).catch(() => {})
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function runAgent(body: RunAgentRequest): Promise<RunAgentResponse> {
  const res = await fetch(`${base()}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson<RunAgentResponse>(res)
}

export async function listCheckpoints(
  threadId: string,
): Promise<CheckpointListResponse> {
  const res = await fetch(`${base()}/api/threads/${encodeURIComponent(threadId)}/checkpoints`)
  return parseJson<CheckpointListResponse>(res)
}

export async function getThreadLatestState(threadId: string): Promise<CheckpointStateResponse> {
  const res = await fetch(`${base()}/api/threads/${encodeURIComponent(threadId)}/state`)
  return parseJson<CheckpointStateResponse>(res)
}

export async function getCheckpointState(
  threadId: string,
  checkpointId: string,
): Promise<CheckpointStateResponse> {
  const res = await fetch(
    `${base()}/api/threads/${encodeURIComponent(threadId)}/checkpoints/${encodeURIComponent(checkpointId)}/state`,
  )
  return parseJson<CheckpointStateResponse>(res)
}
