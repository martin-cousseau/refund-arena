import { CLAUSES } from "@/lib/clauses"
import { FAIL_FLAGS, normalizeScore, primaryFail, type FailFlagKey } from "@/lib/result"
import type { LiveBoard, Score, Ticket, TicketRun } from "@/lib/types"

export type RunLike = {
  ticket_id?: string
  ticket?: Ticket
  title?: string
  score: Score
  tools: string[]
  content?: string | null
}

export function runTicketId(row: RunLike): string {
  return row.ticket_id || row.ticket?.id || ""
}

export function deskPassCount(runs: RunLike[]): number {
  return runs.filter((row) => normalizeScore(row.score).passed_desk).length
}

export function deskPassPct(runs: RunLike[]): number | null {
  if (runs.length === 0) return null
  return Math.round((100 * deskPassCount(runs)) / runs.length)
}

export type MixSlice = {
  key: string
  label: string
  count: number
  color: string
}

export function failMix(runs: RunLike[]): MixSlice[] {
  const counts = new Map<string, number>()
  for (const row of FAIL_FLAGS) counts.set(row.key, 0)
  for (const run of runs) {
    const primary = primaryFail(normalizeScore(run.score))
    if (primary) counts.set(primary.key, (counts.get(primary.key) ?? 0) + 1)
  }
  return FAIL_FLAGS.map((row) => ({
    key: row.key,
    label: row.label,
    count: counts.get(row.key) ?? 0,
    color: row.color,
  })).filter((row) => row.count > 0)
}

export function passByClause(tickets: Ticket[], runs: RunLike[]): { clause: string; ran: number; pass: number; pct: number }[] {
  const byId = new Map(runs.map((row) => [runTicketId(row), row]))
  return CLAUSES.map((clause) => {
    const rows = tickets.filter((ticket) => ticket.clause === clause)
    const ranRows = rows.map((ticket) => byId.get(ticket.id)).filter((row): row is RunLike => Boolean(row))
    const pass = deskPassCount(ranRows)
    const ran = ranRows.length
    return { clause, ran, pass, pct: ran ? Math.round((100 * pass) / ran) : 0 }
  })
}

export type FunnelStep = { step: string; count: number }

export function toolFunnel(runs: RunLike[]): FunnelStep[] {
  const n = runs.length
  const lookup = runs.filter((row) => row.tools.includes("lookup_order")).length
  const policy = runs.filter((row) => row.tools.includes("read_policy")).length
  const wrote = runs.filter(
    (row) => row.tools.includes("issue_refund") || row.tools.includes("escalate")
  ).length
  return [
    { step: "Ran", count: n },
    { step: "lookup_order", count: lookup },
    { step: "read_policy", count: policy },
    { step: "write", count: wrote },
  ]
}

export function trapSplit(tickets: Ticket[], runs: RunLike[]): { label: string; ran: number; pass: number; pct: number }[] {
  const byId = new Map(runs.map((row) => [runTicketId(row), row]))
  const groups = [
    { label: "Trap", rows: tickets.filter((row) => row.trap) },
    { label: "Eligible", rows: tickets.filter((row) => !row.trap) },
  ]
  return groups.map((group) => {
    const ranRows = group.rows.map((ticket) => byId.get(ticket.id)).filter((row): row is RunLike => Boolean(row))
    const pass = deskPassCount(ranRows)
    const ran = ranRows.length
    return { label: group.label, ran, pass, pct: ran ? Math.round((100 * pass) / ran) : 0 }
  })
}

export type FailureRow = {
  ticket_id: string
  title: string
  reason: string
  kind: "gate" | "desk"
}

export function failuresNeedingReview(runs: RunLike[], limit = 8): FailureRow[] {
  const failed = runs
    .map((row) => {
      const score = normalizeScore(row.score)
      if (score.passed_desk) return null
      return {
        ticket_id: runTicketId(row),
        title: row.title || row.ticket?.title || runTicketId(row),
        reason: score.reason || "fail",
        kind: score.forbidden_write ? ("gate" as const) : ("desk" as const),
      }
    })
    .filter((row): row is FailureRow => Boolean(row))
  failed.sort((a, b) => Number(b.kind === "gate") - Number(a.kind === "gate"))
  return failed.slice(0, limit)
}

export function failCount(board: LiveBoard): number {
  return (board.runs ?? []).filter((row) => !normalizeScore(row.score).passed_desk).length
}

export function flagCount(runs: RunLike[], key: FailFlagKey): number {
  return runs.filter((row) => row.score[key]).length
}

export function asRunLike(run: TicketRun): RunLike {
  return {
    ticket_id: run.ticket.id,
    ticket: run.ticket,
    title: run.ticket.title,
    score: normalizeScore(run.score),
    tools: run.tools,
    content: run.content,
  }
}
