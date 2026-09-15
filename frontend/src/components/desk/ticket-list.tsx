import { useEffect } from "react"

import { TicketTags } from "@/components/desk/ticket-tags"
import { ScrollArea } from "@/components/ui/scroll-area"
import { failRowClass } from "@/lib/fail-row"
import type { ResultKind } from "@/lib/result"
import type { Ticket } from "@/lib/types"
import { cn } from "cn"

export type ListedTicket = {
  ticket: Ticket
  result: ResultKind
  running: boolean
}

export function TicketList({
  rows,
  selectedId,
  onSelect,
  pulseGate,
}: {
  rows: ListedTicket[]
  selectedId: string | null
  onSelect: (id: string) => void
  pulseGate?: boolean
}) {
  useEffect(() => {
    if (!selectedId) return
    const el = document.querySelector(`[data-ticket="${selectedId}"]`)
    el?.scrollIntoView({ block: "nearest" })
  }, [selectedId])

  if (rows.length === 0) {
    return <p className="px-3 py-6 text-sm text-muted-foreground">No tickets match these filters.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <ul className="flex flex-col pr-1">
        {rows.map(({ ticket, result, running }) => {
          const selected = ticket.id === selectedId
          const kind = running ? "running" : result
          return (
            <li key={ticket.id}>
              <button
                type="button"
                data-ticket={ticket.id}
                onClick={() => onSelect(ticket.id)}
                className={cn(
                  "flex w-full flex-col gap-1 rounded-md px-2.5 py-2 text-left transition-colors hover:bg-muted/70",
                  failRowClass(kind, selected)
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-muted-foreground">{ticket.id}</span>
                  <span className="min-w-0 truncate text-[13px]">{ticket.title}</span>
                </div>
                <TicketTags ticket={ticket} result={kind} pulse={kind === "gate" && pulseGate} />
              </button>
            </li>
          )
        })}
      </ul>
    </ScrollArea>
  )
}
