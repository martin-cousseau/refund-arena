import type { Ticket, ToolCall } from "@/lib/types"

export type ThreadSource = {
  turns?: { turn: number; content: string }[]
  content?: string | null
  toolCalls?: ToolCall[]
  running: boolean
}

export type CustomerBubble = {
  kind: "customer"
  turn: number
  label: string
  detail?: string
  text: string
}

export type DeskBubble = {
  kind: "desk"
  turn: number
  calls: ToolCall[]
  content: string | null
  pending: boolean
}

export type ThreadBubble = CustomerBubble | DeskBubble

export type ThreadModel = {
  bubbles: ThreadBubble[]
  missingTools: string[]
  idle: boolean
}

function repliesFrom(source: ThreadSource): Map<number, string> {
  const replies = new Map<number, string>()
  for (const turn of source.turns ?? []) {
    if (turn.content.trim()) replies.set(turn.turn, turn.content)
  }
  if (replies.size === 0 && source.content?.trim())
    replies.set(1, source.content)
  return replies
}

function callsFor(calls: ToolCall[], turn: number): ToolCall[] {
  return calls.filter((call) => (call.turn ?? 1) === turn)
}

function customerLabel(
  ticket: Ticket,
  turn: number
): { label: string; detail?: string } {
  const name = ticket.caller?.name
  const label = name
    ? `Customer · turn ${turn} · ${name}`
    : `Customer · turn ${turn}`
  if (turn !== 1 || !ticket.caller) return { label }
  return {
    label,
    detail: `Authenticated ${ticket.caller.customer_id}`,
  }
}

export function buildThread(ticket: Ticket, source: ThreadSource): ThreadModel {
  const replies = repliesFrom(source)
  const calls = source.toolCalls ?? []
  const idle = !source.running && replies.size === 0 && calls.length === 0
  const customerTurns: { turn: number; text: string }[] = [
    { turn: 1, text: ticket.message },
  ]
  if (ticket.follow_up) customerTurns.push({ turn: 2, text: ticket.follow_up })

  const maxTurn = Math.max(
    1,
    ...customerTurns.map((row) => row.turn),
    ...replies.keys(),
    ...calls.map((call) => call.turn ?? 1)
  )

  const bubbles: ThreadBubble[] = []
  for (let turn = 1; turn <= maxTurn; turn += 1) {
    const customer = customerTurns.find((row) => row.turn === turn)
    const previousReady = turn === 1 || replies.has(turn - 1)
    const showCustomer = Boolean(customer) && (!source.running || previousReady)
    if (customer && showCustomer) {
      bubbles.push({
        kind: "customer",
        turn,
        text: customer.text,
        ...customerLabel(ticket, turn),
      })
    }

    const turnCalls = callsFor(calls, turn)
    const reply = replies.get(turn) ?? null
    const waiting =
      source.running &&
      previousReady &&
      reply == null &&
      (turn === 1 || showCustomer)
    const showDesk =
      reply != null ||
      turnCalls.length > 0 ||
      waiting ||
      (showCustomer && !source.running)
    if (showDesk) {
      bubbles.push({
        kind: "desk",
        turn,
        calls: turnCalls,
        content: reply,
        pending: waiting,
      })
    }
  }

  const names = new Set(calls.map((call) => call.name))
  const missingTools =
    source.running || idle
      ? []
      : (ticket.gold_tools ?? []).filter((name) => !names.has(name))

  return { bubbles, missingTools, idle }
}
