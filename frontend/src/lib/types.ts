export type GoldWrite = "none" | "issue_refund" | "escalate"

export type Caller = {
  customer_id: string
  name: string
  email: string
}

export type Ticket = {
  id: string
  title: string
  message: string
  trap: boolean
  gold_write: GoldWrite
  gold_order_id?: string
  gold_amount_eur?: number
  forbidden_order_id?: string
  gold_tools?: string[]
  clause: string
  style?: string
  attack?: string
  source?: string
  notes?: string
  caller?: Caller
  follow_up?: string
  names_order_ids?: boolean
  hole?: string
  stale?: boolean
}

export type Order = {
  id: string
  sku: string
  customer: string
  channel: string
  delivered_at: string
  days_since_delivery: number
  status: string
  amount_eur: number
  currency: string
  sale: boolean
  already_refunded: boolean
  tags_on: boolean
  refund_window_days: number
  pair_id?: string
  pair_role?: string
  sku_family?: string
  customer_id?: string
}

export type Payment = {
  order_id: string
  amount_eur: number
  currency: string
  at: string
  source: string
}

export type Escalation = {
  order_id: string
  reason: string
  at: string
}

export type Score = {
  forbidden_write: boolean
  missing_read: boolean
  lying_close: boolean
  closed: boolean
  missed_refund: boolean
  missed_escalate: boolean
  wrong_amount: boolean
  near_miss: boolean
  caved: boolean
  reason: string
  passed_gate: boolean
  passed_desk: boolean
}

export type ToolCall = {
  name: string
  args: Record<string, unknown>
  result: unknown
  turn?: number
}

export type PolicyPage = {
  id: string
  title: string
  updated: string
  status: string
  text?: string
}

export type RefundService = {
  checks: string[]
  does_not_check: string[]
}

export type PromptConfig = {
  id: string
  name: string
  builtin: boolean
  model: string
  instructions: string
  created_at?: string
  updated_at?: string
}

export type TicketRun = {
  ticket: Ticket
  config_id: string
  content: string | null
  turns?: { turn: number; content: string }[]
  tools: string[]
  tool_calls: ToolCall[]
  score: Score
  payments_delta: Payment[]
  escalations_delta: Escalation[]
  payments: Payment[]
  escalations: Escalation[]
  orders: Order[]
  board?: LiveBoard
}

export type World = {
  policy: string
  orders: Order[]
  tickets: Ticket[]
  payments: Payment[]
  escalations: Escalation[]
  refund_window_days: number
  amount_cap_eur: number
  trap_order_ids: string[]
  policy_pages?: PolicyPage[]
  service?: RefundService
  configs?: PromptConfig[]
  model?: string
  xai_signed_in?: boolean
}

export type BoardRun = {
  ticket_id: string
  title?: string
  score: Score
  content?: string | null
  tools: string[]
}

export type LiveBoard = {
  ran: number
  total: number
  closed_tickets: number
  forbidden_write: 0 | 1
  gate_fail?: 0 | 1
  missed_refund: number
  missed_escalate: number
  wrong_amount: number
  missing_read: number
  lying_close: number
  near_miss: number
  caved: number
  config_id?: string
  runs?: BoardRun[]
}

export type JobItem = {
  ticket_id: string
  title?: string
  status: "queued" | "running" | "done" | "error" | "cancelled"
  error?: string | null
  score?: Score | null
  reason?: string | null
}

export type ArenaJob = {
  id: string
  config_id: string
  status: "queued" | "running" | "cancelling" | "done" | "cancelled" | "failed"
  concurrency: number
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  total: number
  done: number
  error?: string | null
  board?: LiveBoard | null
  items: JobItem[]
}
