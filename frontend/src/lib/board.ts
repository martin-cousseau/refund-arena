import type { LiveBoard, TicketRun } from "@/lib/types"

export function emptyBoard(total: number, configId?: string): LiveBoard {
  return {
    ran: 0,
    total,
    closed_tickets: 0,
    forbidden_write: 0,
    missed_refund: 0,
    missed_escalate: 0,
    wrong_amount: 0,
    missing_read: 0,
    lying_close: 0,
    unsolicited_write: 0,
    config_id: configId,
  }
}

export function liveBoard(runs: Record<string, TicketRun>, total: number, configId?: string): LiveBoard {
  const list = Object.values(runs)
  const n = list.length
  return {
    ran: n,
    total,
    closed_tickets: n ? Math.round((100 * list.filter((row) => row.score.closed).length) / n) : 0,
    forbidden_write: list.some((row) => row.score.forbidden_write) ? 1 : 0,
    missed_refund: list.filter((row) => row.score.missed_refund).length,
    missed_escalate: list.filter((row) => row.score.missed_escalate).length,
    wrong_amount: list.filter((row) => row.score.wrong_amount).length,
    missing_read: list.filter((row) => row.score.missing_read).length,
    lying_close: list.filter((row) => row.score.lying_close).length,
    unsolicited_write: list.filter((row) => row.score.unsolicited_write).length,
    config_id: configId,
  }
}

export function paymentKey(row: { order_id: string; at: string; source: string }): string {
  return `${row.order_id}|${row.at}|${row.source}`
}
