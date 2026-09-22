import { normalizeScore } from "@/lib/result"
import type { ArenaJob, LiveBoard, PromptConfig, TicketRun, World } from "@/lib/types"

function messageFromBody(status: number, raw: string, label: string): string {
  const trimmed = raw.trim()
  if (status === 502 || status === 503 || status === 504 || trimmed.startsWith("<")) {
    return "Backend is starting or unreachable. Retry in a moment."
  }
  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown }
    if (typeof parsed.detail === "string" && parsed.detail.trim()) return parsed.detail
  } catch {
    // not JSON
  }
  if (trimmed && trimmed.length < 200 && !trimmed.startsWith("<")) return trimmed
  return `${label} failed (${status})`
}

async function readJson<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    throw new Error(messageFromBody(res.status, await res.text(), label))
  }
  return (await res.json()) as T
}

async function getJson<T>(url: string, label: string, attempts = 8): Promise<T> {
  let last = new Error(label)
  for (let i = 0; i < attempts; i++) {
    try {
      return await readJson<T>(await fetch(url), label)
    } catch (err) {
      last = err instanceof Error ? err : new Error(String(err))
      const retryable = /starting or unreachable|Failed to fetch|NetworkError/i.test(last.message)
      if (!retryable || i === attempts - 1) throw last
      await new Promise((resolve) => setTimeout(resolve, 750))
    }
  }
  throw last
}

export async function fetchWorld(): Promise<World> {
  return getJson<World>("/arena/world", "Load world")
}

export async function fetchConfigs(): Promise<PromptConfig[]> {
  const payload = await readJson<{ configs: PromptConfig[] }>(await fetch("/arena/configs"), "Load configs")
  return payload.configs
}

function withNormalizedBoard(board: LiveBoard): LiveBoard {
  return {
    ...board,
    runs: (board.runs ?? []).map((row) => ({ ...row, score: normalizeScore(row.score) })),
  }
}

export async function fetchBoard(configId: string): Promise<LiveBoard> {
  const board = await getJson<LiveBoard>(
    `/arena/board?config_id=${encodeURIComponent(configId)}`,
    "Load board"
  )
  return withNormalizedBoard(board)
}

export async function fetchRuns(configId: string): Promise<TicketRun[]> {
  const payload = await getJson<{ config_id: string; runs: TicketRun[] }>(
    `/arena/runs?config_id=${encodeURIComponent(configId)}`,
    "Load runs"
  )
  return payload.runs.map((row) => ({ ...row, score: normalizeScore(row.score) }))
}

export async function runTicket(ticketId: string, configId: string): Promise<TicketRun> {
  const res = await fetch("/arena/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket_id: ticketId, config_id: configId }),
  })
  const payload = await readJson<TicketRun>(res, `Run ${ticketId}`)
  return {
    ...payload,
    score: normalizeScore(payload.score),
    board: payload.board
      ? {
          ...payload.board,
          runs: (payload.board.runs ?? []).map((row) => ({ ...row, score: normalizeScore(row.score) })),
        }
      : payload.board,
  }
}

export async function submitJob(body: {
  config_id: string
  ticket_ids?: string[]
  sample?: number
  all?: boolean
  concurrency?: number
}): Promise<ArenaJob> {
  const res = await fetch("/arena/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return readJson<ArenaJob>(res, "Queue job")
}

export async function fetchJob(jobId: string): Promise<ArenaJob> {
  return readJson<ArenaJob>(await fetch(`/arena/jobs/${jobId}`), "Job")
}

export async function cancelJob(jobId: string): Promise<ArenaJob> {
  const res = await fetch(`/arena/jobs/${jobId}/cancel`, { method: "POST" })
  return readJson<ArenaJob>(res, "Cancel job")
}

export async function createConfig(body: {
  name: string
  instructions: string
  clone_from?: string
}): Promise<PromptConfig> {
  const res = await fetch("/arena/configs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return readJson<PromptConfig>(res, "Create config")
}

export async function updateConfig(
  id: string,
  body: { name?: string; instructions?: string }
): Promise<PromptConfig> {
  const res = await fetch(`/arena/configs/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return readJson<PromptConfig>(res, "Save config")
}

export async function deleteConfig(id: string): Promise<void> {
  const res = await fetch(`/arena/configs/${encodeURIComponent(id)}`, { method: "DELETE" })
  await readJson<{ ok: boolean }>(res, "Delete config")
}

export async function resetConfig(id: string): Promise<PromptConfig> {
  const res = await fetch(`/arena/configs/${encodeURIComponent(id)}/reset`, { method: "POST" })
  return readJson<PromptConfig>(res, "Reset config")
}

export async function resetRuns(configId: string): Promise<LiveBoard> {
  const res = await fetch("/arena/runs/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config_id: configId }),
  })
  const payload = await readJson<{ board: LiveBoard }>(res, "Reset runs")
  return withNormalizedBoard(payload.board)
}
