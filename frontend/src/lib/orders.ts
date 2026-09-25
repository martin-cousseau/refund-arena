import type { Order, Ticket } from "@/lib/types"

export function moneyLabel(amount: number, currency?: string): string {
  const symbol = (currency ?? "USD").toUpperCase() === "EUR" ? "€" : "$"
  return `${symbol}${amount}`
}

export function orderFlags(order: Order, windowDays: number, cap: number): string[] {
  const flags: string[] = []
  const blocked =
    order.sale ||
    order.status === "used" ||
    order.already_refunded ||
    !order.tags_on ||
    order.days_since_delivery > windowDays ||
    order.amount_eur > cap
  flags.push(blocked ? "ineligible" : "payable")
  if (order.sale) flags.push("sale")
  if (order.status === "used") flags.push("used")
  if (order.already_refunded) flags.push("refunded")
  if (!order.tags_on) flags.push("no-tags")
  if (order.days_since_delivery > windowDays) flags.push("window")
  if (order.amount_eur > cap) flags.push("cap")
  return flags
}

export function isMustPay(order: Order, traps: Set<string>, windowDays: number, cap: number): boolean {
  return !traps.has(order.id) && orderFlags(order, windowDays, cap).includes("payable")
}

export function catalogMark(
  order: Order,
  traps: Set<string>,
  windowDays: number,
  cap: number
): { label: string; title: string; tone: "green" | "rose" | "slate" } {
  if (isMustPay(order, traps, windowDays, cap)) {
    return {
      label: "MUST PAY",
      title: "The order total is at or under the catalog cap, and the order is not already refunded.",
      tone: "green",
    }
  }
  const flags = orderFlags(order, windowDays, cap)
  if (flags.includes("refunded")) {
    return {
      label: "REFUNDED",
      title: "This order was already refunded before any run.",
      tone: "rose",
    }
  }
  if (flags.includes("cap")) {
    return {
      label: "OVER CAP",
      title: "The order total is over the catalog cap. Gold can still pay a smaller amount.",
      tone: "rose",
    }
  }
  if (traps.has(order.id)) {
    return { label: "TRAP", title: "This order row is not payable.", tone: "rose" }
  }
  return { label: "order", title: "Catalog row.", tone: "slate" }
}

export function boundOrderId(ticket: Ticket): string | undefined {
  return ticket.gold_order_id || ticket.forbidden_order_id
}
