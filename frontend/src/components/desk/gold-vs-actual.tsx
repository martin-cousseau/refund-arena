import { Tag } from "@/components/ui/tag"
import { goldLabel } from "@/lib/clauses"
import type { Ticket, TicketRun } from "@/lib/types"

type CheckStatus = "match" | "miss"

function Check({ status, label, detail }: { status: CheckStatus; label: string; detail?: string }) {
  return (
    <div className="flex items-start justify-between gap-2 text-[12px]">
      <div>
        <div>{label}</div>
        {detail ? <p className="font-mono text-[11px] text-muted-foreground">{detail}</p> : null}
      </div>
      <Tag tone={status === "match" ? "green" : "rose"}>{status}</Tag>
    </div>
  )
}

function decisionLines(run: TicketRun): string {
  const lines = run.tool_calls
    .filter((call) => call.name === "propose_refund" || call.name === "propose_handoff")
    .map((call) => {
      const oid = String(call.args.order_id ?? "")
      const raw = call.result
      let decision = call.name === "propose_handoff" ? "queue" : ""
      if (raw && typeof raw === "object" && "decision" in raw) decision = String((raw as { decision?: unknown }).decision ?? decision)
      if (typeof raw === "string") {
        try {
          decision = String((JSON.parse(raw) as { decision?: string }).decision ?? decision)
        } catch {
          /* result is prose */
        }
      }
      return `${oid || "?"} ${decision || call.name}`
    })
  return lines.join(", ")
}

export function GoldVsActual({ ticket, run }: { ticket: Ticket; run?: TicketRun | null }) {
  const goldWrite = ticket.gold_write
  const paid = (run?.payments_delta ?? []).filter((row) => row.source === "commit" || row.source === "issue_refund")
  const score = run?.score
  const proposalMiss = Boolean(
    score && (score.near_miss || score.missed_refund || score.missed_escalate || score.forbidden_write || score.caved)
  )
  const ledgerMiss = Boolean(score && (score.forbidden_write || score.missed_refund || score.wrong_amount))

  return (
    <div className="flex flex-col gap-3">
      <section>
        <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Gold</h3>
        <div className="flex flex-wrap gap-1">
          <Tag tone={goldWrite === "issue_refund" ? "green" : goldWrite === "escalate" ? "amber" : "slate"}>
            {goldLabel(goldWrite, ticket.gold_amount_eur, ticket.gold_order_id || ticket.forbidden_order_id)}
          </Tag>
          {ticket.hole === "ownership" ? <Tag tone="rose">ownership hole</Tag> : null}
          {ticket.forbidden_order_id ? <Tag tone="rose">forbid {ticket.forbidden_order_id}</Tag> : null}
        </div>
        {ticket.caller ? (
          <p className="mt-1 font-mono text-[11px] text-muted-foreground">
            caller {ticket.caller.name} · {ticket.caller.customer_id}
          </p>
        ) : null}
      </section>
      <section>
        <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Seams</h3>
        {run && score ? (
          <div className="flex flex-col gap-1.5">
            <Check status={proposalMiss ? "miss" : "match"} label="Proposal" detail={run.tools.filter((name) => name.startsWith("propose_")).join(", ") || "none"} />
            <Check
              status={score.forbidden_write ? "miss" : "match"}
              label="Decision"
              detail={decisionLines(run) || "no service call"}
            />
            <Check
              status={ledgerMiss ? "miss" : "match"}
              label="Ledger"
              detail={paid.length ? paid.map((row) => `${row.order_id} €${row.amount_eur}`).join(", ") : "no new payment"}
            />
            <Check status={score.lying_close ? "miss" : "match"} label="Reply" detail={score.lying_close ? "claim disagrees with the ledger" : "matches the ledger"} />
          </div>
        ) : (
          <p className="text-[12px] text-muted-foreground">Not run on this config yet.</p>
        )}
      </section>
    </div>
  )
}
