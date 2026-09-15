import { normalizeScore } from "@/lib/result"
import type { ArenaJob, LiveBoard, PromptConfig, TicketRun, World } from "@/lib/types"

async function readJson<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    const raw = await res.text()
    let detail = raw
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown }
      if (typeof parsed.detail === "string") detail = parsed.detail
    } catch {
      // keep the raw body
    }
    throw new Error(detail || `${label} failed (${res.status})`)
  }
  return (await res.json()) as T
}

export async function fetchWorld(): Promise<World> {
  return readJson<World>(await fetch("/arena/world"), "Load world")
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
  const board = await readJson<LiveBoard>(
    await fetch(`/arena/board?config_id=${encodeURIComponent(configId)}`),
    "Load board"
  )
  return withNormalizedBoard(board)
}

export async function fetchRuns(configId: string): Promise<TicketRun[]> {
  const payload = await readJson<{ config_id: string; runs: TicketRun[] }>(
    await fetch(`/arena/runs?config_id=${encodeURIComponent(configId)}`),
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
