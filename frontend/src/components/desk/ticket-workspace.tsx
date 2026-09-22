import { useEffect, useState } from "react"

import { GoldVsActual } from "@/components/desk/gold-vs-actual"
import { OrderCard } from "@/components/desk/order-card"
import { ScoreBanner } from "@/components/desk/score-banner"
import { TicketTags } from "@/components/desk/ticket-tags"
import { Transcript } from "@/components/desk/transcript"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { fetchLive } from "@/lib/api"
import { CLAUSE_BLURB } from "@/lib/clauses"
import { boundOrderId } from "@/lib/orders"
import { resultFromScore } from "@/lib/result"
import type { LiveSnapshot, Order, Ticket, TicketRun } from "@/lib/types"
import { cn } from "cn"

export function TicketWorkspace({
  ticket,
  run,
  running,
  pendingNote,
  busy,
  configId,
  onRun,
  className,
}: {
  ticket: Ticket
  run: TicketRun | null
  running: boolean
  pendingNote: string
  busy: boolean
  configId: string
  onRun: () => void
  className?: string
}) {
  const [live, setLive] = useState<LiveSnapshot | null>(null)
  const kind = running ? "running" : resultFromScore(run?.score)

  useEffect(() => {
    setLive(null)
  }, [ticket.id])

  useEffect(() => {
    if (!running) return undefined
    let cancelled = false
    const tick = () => {
      void fetchLive(ticket.id, configId)
        .then((snap) => {
          if (!cancelled && snap) setLive(snap)
        })
        .catch(() => undefined)
    }
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [configId, running, ticket.id])

  return (
    <div
      className={cn(
        "flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card",
        className
      )}
    >
      <header className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-mono text-sm">{ticket.id}</h2>
            <TicketTags ticket={ticket} result={kind} pulse={kind === "gate"} />
          </div>
          <p className="mt-1 text-sm">{ticket.title}</p>
        </div>
        <Button size="sm" disabled={busy} onClick={onRun}>
          Run ticket
        </Button>
      </header>
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-4 p-4">
          {run?.score && !running ? (
            <ScoreBanner
              score={run.score}
              trapOrderId={ticket.forbidden_order_id}
              paid={(run.payments_delta ?? []).some(
                (row) =>
                  row.source === "commit" || row.source === "issue_refund"
              )}
              configId={run.config_id}
            />
          ) : null}
          <Transcript
            ticket={ticket}
            run={run}
            live={live}
            running={running}
            pendingNote={pendingNote}
          />
        </div>
      </ScrollArea>
    </div>
  )
}

export function TicketProperties({
  ticket,
  run,
  orders,
  trapIds,
  windowDays,
  cap,
}: {
  ticket: Ticket
  run: TicketRun | null
  orders: Order[]
  trapIds: Set<string>
  windowDays: number
  cap: number
}) {
  const orderId = boundOrderId(ticket)
  const order = orders.find((row) => row.id === orderId)

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-4 p-3">
        <GoldVsActual ticket={ticket} run={run} />
        {order ? (
          <section>
            <h3 className="mb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
              Order
            </h3>
            <OrderCard
              order={order}
              trapIds={trapIds}
              windowDays={windowDays}
              cap={cap}
              compact
            />
          </section>
        ) : (
          <p className="text-[12px] text-muted-foreground">
            No bound order. Info tickets may not name a row.
          </p>
        )}
        <section>
          <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            Clause
          </h3>
          <p className="text-[12px] leading-relaxed text-muted-foreground">
            {CLAUSE_BLURB[ticket.clause] ?? ticket.clause}
          </p>
        </section>
        <section>
          <h3 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            Meta
          </h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-[11px]">
            <dt className="text-muted-foreground">style</dt>
            <dd>{ticket.style ?? "—"}</dd>
            <dt className="text-muted-foreground">attack</dt>
            <dd>{ticket.attack ?? "—"}</dd>
            <dt className="text-muted-foreground">source</dt>
            <dd className="truncate">{ticket.source ?? "—"}</dd>
          </dl>
        </section>
      </div>
    </ScrollArea>
  )
}
