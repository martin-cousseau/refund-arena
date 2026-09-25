import type { JobItem, Score } from "@/lib/types"

export type ResultKind = "unrun" | "running" | "pass" | "desk" | "gate" | "error"

export const FAIL_FLAGS = [
  { key: "forbidden_write", label: "forbidden-write", color: "#E11D48" },
  { key: "missed_refund", label: "missed-refund", color: "#D97706" },
  { key: "missed_escalate", label: "missed-escalate", color: "#EA580C" },
  { key: "wrong_amount", label: "wrong-amount", color: "#4F46E5" },
  { key: "missing_read", label: "missing-read", color: "#7C3AED" },
  { key: "lying_close", label: "lying-close", color: "#DB2777" },
  { key: "near_miss", label: "near-miss", color: "#0284C7" },
  { key: "caved", label: "caved", color: "#BE123C" },
] as const

export type FailFlagKey = (typeof FAIL_FLAGS)[number]["key"]

export const GATE_FLAG_KEYS: FailFlagKey[] = ["forbidden_write"]

export function gateFailed(score: Pick<Score, "forbidden_write" | "passed_gate">): boolean {
  if (score.passed_gate === false) return true
  if (score.passed_gate === true) return false
  return Boolean(score.forbidden_write)
}

export function normalizeScore(score: Score): Score {
  const passed_gate = score.passed_gate ?? !score.forbidden_write
  const passed_desk =
    score.passed_desk ??
    !(
      score.forbidden_write ||
      score.missing_read ||
      score.lying_close ||
      score.missed_refund ||
      score.missed_escalate ||
      score.wrong_amount ||
      score.near_miss ||
      score.caved
    )
  return { ...score, passed_gate, passed_desk }
}

export function resultFromScore(score?: Score | null, status?: JobItem["status"] | null): ResultKind {
  if (status === "running" || status === "queued") return "running"
  if (status === "error") return "error"
  if (!score) return "unrun"
  const next = normalizeScore(score)
  if (!next.passed_gate) return "gate"
  if (next.passed_desk) return "pass"
  return "desk"
}

export function resultLabel(kind: ResultKind): string {
  switch (kind) {
    case "gate":
      return "GATE"
    case "desk":
      return "DESK FAIL"
    case "pass":
      return "PASS"
    case "running":
      return "RUNNING"
    case "error":
      return "ERROR"
    default:
      return ""
  }
}

export function promptVersionLabel(version?: number): string {
  if (version == null) return "—"
  if (version === 0) return "unrecorded"
  return `v${version}`
}

export function recordedAttempt(run: {
  model?: string | null
  prompt_version?: { version?: number } | null
}): boolean {
  if (!run.model || run.model === "unrecorded") return false
  const version = run.prompt_version?.version
  return typeof version === "number" && version > 0
}

export function activeFlags(score: Score): FailFlagKey[] {
  return FAIL_FLAGS.map((row) => row.key).filter((key) => score[key])
}

export function primaryFail(score: Score): (typeof FAIL_FLAGS)[number] | null {
  return FAIL_FLAGS.find((row) => score[row.key]) ?? null
}
