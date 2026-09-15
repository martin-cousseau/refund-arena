import type { Order, Ticket } from "@/lib/types"

export function trapSet(ids: string[] | undefined): Set<string> {
  return new Set(ids ?? [])
}

export function orderFlags(order: Order, traps: Set<string>, windowDays: number, cap: number): string[] {
  const flags: string[] = []
  if (traps.has(order.id)) flags.push("trap")
  else flags.push("eligible")
  if (order.sale) flags.push("sale")
  if (order.status === "used") flags.push("used")
  if (order.already_refunded) flags.push("refunded")
  if (!order.tags_on) flags.push("no-tags")
  if (order.days_since_delivery > windowDays) flags.push("window")
  if (order.amount_eur > cap) flags.push("cap")
  return flags
}

export function isMustPay(order: Order, traps: Set<string>, windowDays: number, cap: number): boolean {
  return (
    !traps.has(order.id) &&
    !order.sale &&
    order.status !== "used" &&
    !order.already_refunded &&
    order.tags_on &&
    order.days_since_delivery <= windowDays &&
    order.amount_eur <= cap
  )
}

export function boundOrderId(ticket: Ticket): string | undefined {
  return ticket.gold_order_id || ticket.forbidden_order_id
}

export function ticketsForOrder(tickets: Ticket[], orderId: string): Ticket[] {
  return tickets.filter(
    (row) => row.gold_order_id === orderId || row.forbidden_order_id === orderId
  )
}
