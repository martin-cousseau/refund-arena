import { ResultTag, Tag } from "@/components/ui/tag"
import { CLAUSE_TONE, GOLD_TONE } from "@/lib/clauses"
import type { ResultKind } from "@/lib/result"
import type { Ticket } from "@/lib/types"

export function TicketTags({
  ticket,
  result,
  pulse,
}: {
  ticket: Ticket
  result?: ResultKind
  pulse?: boolean
}) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <Tag tone={CLAUSE_TONE[ticket.clause] ?? "slate"}>{ticket.clause}</Tag>
      {ticket.trap ? (
        <Tag tone="rose" solid>
          trap
        </Tag>
      ) : null}
      {ticket.gold_write !== "none" ? (
        <Tag tone={GOLD_TONE[ticket.gold_write] ?? "slate"}>
          {ticket.gold_write === "issue_refund" ? "refund" : "escalate"}
        </Tag>
      ) : null}
      {result ? <ResultTag kind={result} pulse={pulse} /> : null}
    </div>
  )
}
