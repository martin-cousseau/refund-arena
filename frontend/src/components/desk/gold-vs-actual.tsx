import { Tag } from "@/components/ui/tag"
import { goldLabel } from "@/lib/clauses"
import type { GoldWrite, Ticket, TicketRun } from "@/lib/types"

type CheckStatus = "match" | "miss" | "extra"

function Check({ status, label }: { status: CheckStatus; label: string }) {
  return (
    <div className="flex items-center justify-between gap-2 text-[12px]">
      <span>{label}</span>
      <Tag tone={status === "match" ? "green" : status === "extra" ? "amber" : "rose"}>
        {status}
      </Tag>
    </div>
  )
}

function actualWriteOf(run: TicketRun): GoldWrite {
  if (run.tools.includes("issue_refund")) return "issue_refund"
  if (run.tools.includes("escalate")) return "escalate"
  return "none"
}

function writeStatus(gold: GoldWrite, actual: GoldWrite): CheckStatus {
  if (actual === gold) return "match"
  if (gold === "none" && actual === "escalate") return "extra"
  return "miss"
}

export function GoldVsActual({ ticket, run }: { ticket: Ticket; run?: TicketRun | null }) {
  const goldWrite = ticket.gold_write
  const actualWrite = run ? actualWriteOf(run) : "none"
  const paid = (run?.payments_delta ?? []).filter((row) => row.source === "issue_refund")
  const goldToolsOk =
    !ticket.gold_tools?.length || ticket.gold_tools.every((name) => run?.tools.includes(name))

  return (
    <div className="flex flex-col gap-3">
      <section>
        <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Gold</h3>
        <div className="flex flex-wrap gap-1">
          <Tag tone={goldWrite === "issue_refund" ? "green" : goldWrite === "escalate" ? "amber" : "slate"}>
            {goldLabel(goldWrite, ticket.gold_amount_eur, ticket.gold_order_id)}
          </Tag>
          {ticket.forbidden_order_id ? <Tag tone="rose">trap {ticket.forbidden_order_id}</Tag> : null}
        </div>
        {ticket.gold_tools?.length ? (
          <p className="mt-1 font-mono text-[11px] text-muted-foreground">{ticket.gold_tools.join(" → ")}</p>
        ) : null}
      </section>
      <section>
        <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Actual</h3>
        {run ? (
          <div className="flex flex-col gap-1.5">
            <Check status={writeStatus(goldWrite, actualWrite)} label={`write · ${actualWrite}`} />
            <Check status={goldToolsOk ? "match" : "miss"} label="required reads" />
            {paid.length > 0 ? (
              <p className="font-mono text-[11px] text-tag-rose">
                paid {paid.map((row) => `${row.order_id} €${row.amount_eur}`).join(", ")}
              </p>
            ) : (
              <p className="font-mono text-[11px] text-muted-foreground">no new payment</p>
            )}
            {(run.escalations_delta ?? []).length > 0 ? (
              <p className="font-mono text-[11px]">
                escalated {run.escalations_delta.map((row) => row.order_id).join(", ")}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="text-[12px] text-muted-foreground">Not run on this config yet.</p>
        )}
      </section>
    </div>
  )
}
