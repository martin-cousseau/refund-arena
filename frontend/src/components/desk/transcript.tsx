import { useEffect, useRef } from "react"

import { ToolTrail } from "@/components/desk/tool-trail"
import { buildThread, type DeskBubble, type ThreadBubble } from "@/lib/thread"
import type { LiveSnapshot, Ticket, TicketRun } from "@/lib/types"

function RichText({ text }: { text: string }) {
  const parts = text.split("**")
  return (
    <p className="text-[13px] leading-relaxed whitespace-pre-wrap">
      {parts.map((part, index) =>
        index % 2 === 1 ? (
          <strong key={index} className="font-medium">
            {part}
          </strong>
        ) : (
          <span key={index}>{part}</span>
        )
      )}
    </p>
  )
}

function DeskBody({
  bubble,
  ticket,
  idle,
  pendingNote,
}: {
  bubble: DeskBubble
  ticket: Ticket
  idle: boolean
  pendingNote: string
}) {
  if (bubble.pending) {
    return <p className="text-[13px] text-muted-foreground">{pendingNote}</p>
  }
  if (bubble.content == null && bubble.calls.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground">
        {idle ? "Not run yet." : "No reply on this turn."}
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-2">
      {bubble.calls.length > 0 ? (
        <ToolTrail
          ticket={ticket}
          calls={bubble.calls}
          showMissing={false}
          hideTurn
        />
      ) : (
        <p className="font-mono text-[11px] text-muted-foreground">
          No new tools.
        </p>
      )}
      {bubble.content ? <RichText text={bubble.content} /> : null}
    </div>
  )
}

function Bubble({
  bubble,
  ticket,
  idle,
  pendingNote,
}: {
  bubble: ThreadBubble
  ticket: Ticket
  idle: boolean
  pendingNote: string
}) {
  if (bubble.kind === "customer") {
    return (
      <article
        data-bubble="customer"
        data-turn={bubble.turn}
        className="rounded-lg bg-muted/70 px-3 py-2.5"
      >
        <p className="mb-1 font-mono text-[11px] text-muted-foreground">
          {bubble.label}
        </p>
        {bubble.detail ? (
          <p className="mb-1.5 font-mono text-[11px] text-muted-foreground">
            {bubble.detail}
          </p>
        ) : null}
        <RichText text={bubble.text} />
      </article>
    )
  }
  return (
    <article
      data-bubble="desk"
      data-turn={bubble.turn}
      className="rounded-lg border border-l-2 border-l-tag-green/70 px-3 py-2.5"
    >
      <p className="mb-2 font-mono text-[11px] text-muted-foreground">
        Desk · turn {bubble.turn}
      </p>
      <DeskBody
        bubble={bubble}
        ticket={ticket}
        idle={idle}
        pendingNote={pendingNote}
      />
    </article>
  )
}

export function Transcript({
  ticket,
  run,
  live,
  running,
  pendingNote,
}: {
  ticket: Ticket
  run: TicketRun | null
  live: LiveSnapshot | null
  running: boolean
  pendingNote: string
}) {
  const endRef = useRef<HTMLDivElement>(null)
  const thread = buildThread(ticket, {
    turns: running ? live?.turns : run?.turns,
    content: running ? null : run?.content,
    toolCalls: running ? (live?.tool_calls ?? []) : (run?.tool_calls ?? []),
    running,
  })

  useEffect(() => {
    if (!running) return
    endRef.current?.scrollIntoView({ block: "nearest" })
  }, [running, thread.bubbles.length, live?.epoch])

  return (
    <section data-transcript="">
      <h3 className="mb-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        Conversation
      </h3>
      <div className="flex flex-col gap-3">
        {thread.bubbles.map((bubble) => (
          <Bubble
            key={`${bubble.kind}-${bubble.turn}`}
            bubble={bubble}
            ticket={ticket}
            idle={thread.idle}
            pendingNote={pendingNote}
          />
        ))}
        {thread.idle ? (
          <p className="text-[13px] text-muted-foreground">
            Queue it, or run this ticket.
          </p>
        ) : null}
        {thread.missingTools.map((name) => (
          <p
            key={name}
            className="rounded-md border border-dashed border-tag-amber/50 px-3 py-2 font-mono text-[12px] text-muted-foreground"
          >
            {name} · not called
          </p>
        ))}
      </div>
      <div ref={endRef} />
    </section>
  )
}
