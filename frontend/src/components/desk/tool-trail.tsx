import { useState } from "react"

import type { Ticket, ToolCall } from "@/lib/types"
import { cn } from "cn"

function stringify(value: unknown): string {
  if (value == null) return ""
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function decisionOf(call: ToolCall): string {
  const result = call.result
  if (result && typeof result === "object" && "decision" in result) {
    return String((result as { decision?: unknown }).decision ?? "")
  }
  if (typeof result === "string") {
    try {
      const parsed = JSON.parse(result) as { decision?: string }
      return parsed.decision ?? ""
    } catch {
      return ""
    }
  }
  return ""
}

export function ToolTrail({
  ticket,
  calls,
}: {
  ticket: Ticket
  calls: ToolCall[]
}) {
  const names = calls.map((call) => call.name)
  const gold = ticket.gold_tools ?? []
  const missing = gold.filter((name) => !names.includes(name))

  return (
    <ol className="flex flex-col gap-1.5">
      {calls.length === 0 ? <p className="text-sm text-muted-foreground">No tool calls.</p> : null}
      {calls.map((call, index) => {
        const oid = String(call.args.order_id ?? call.args.orderId ?? "")
        const decision = decisionOf(call)
        const committedForbidden =
          call.name === "propose_refund" && decision === "commit" && oid && oid === ticket.forbidden_order_id
        const rejected = call.name === "propose_refund" && decision === "reject"
        return (
          <TrailRow
            key={`${call.name}-${index}`}
            name={call.name}
            args={call.args}
            result={call.result}
            turn={call.turn}
            tone={committedForbidden ? "bad" : rejected ? "near" : "plain"}
          />
        )
      })}
      {missing.map((name) => (
        <li
          key={`missing-${name}`}
          className="rounded-md border border-dashed border-tag-amber/50 px-3 py-2 font-mono text-[12px] text-muted-foreground"
        >
          {name} · not called
        </li>
      ))}
    </ol>
  )
}

function TrailRow({
  name,
  args,
  result,
  turn,
  tone,
}: {
  name: string
  args: Record<string, unknown>
  result: unknown
  turn?: number
  tone: "bad" | "near" | "plain"
}) {
  const [open, setOpen] = useState(false)
  const argText = Object.entries(args)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join("  ")
  const resultText = stringify(result)

  return (
    <li
      className={cn(
        "rounded-md border px-3 py-2 font-mono text-[12px]",
        tone === "bad" &&
          "border-tag-rose/40 bg-[repeating-linear-gradient(-45deg,transparent,transparent_6px,color-mix(in_oklch,var(--tag-rose)_12%,transparent)_6px,color-mix(in_oklch,var(--tag-rose)_12%,transparent)_12px)]",
        tone === "near" && "border-tag-amber/50 bg-tag-amber/10"
      )}
    >
      <button type="button" className="flex w-full items-start justify-between gap-2 text-left" onClick={() => setOpen((v) => !v)}>
        <div>
          <div className={cn("font-medium", tone === "bad" && "text-tag-rose", tone === "near" && "text-tag-amber")}>
            {turn ? `t${turn} ` : ""}
            {name}
          </div>
          {argText ? <div className="text-muted-foreground">{argText}</div> : null}
        </div>
        {resultText ? <span className="text-[11px] text-muted-foreground">{open ? "hide" : "result"}</span> : null}
      </button>
      {open && resultText ? (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-muted-foreground">{resultText}</pre>
      ) : null}
    </li>
  )
}
