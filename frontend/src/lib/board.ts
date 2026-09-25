import type { LiveBoard } from "@/lib/types"

export function emptyBoard(total: number, configId?: string): LiveBoard {
  return {
    ran: 0,
    total,
    closed_tickets: 0,
    forbidden_write: 0,
    gate_fail: 0,
    missed_refund: 0,
    missed_escalate: 0,
    wrong_amount: 0,
    missing_read: 0,
    lying_close: 0,
    near_miss: 0,
    caved: 0,
    config_id: configId,
  }
}
