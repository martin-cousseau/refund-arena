import { Tag } from "@/components/ui/tag"
import { CLAUSE_TONE } from "@/lib/clauses"
import { catalogMark, moneyLabel, orderFlags } from "@/lib/orders"
import type { Order } from "@/lib/types"
import { cn } from "cn"

export function OrderCard({
  order,
  trapIds,
  windowDays,
  cap,
  compact = false,
  onClick,
}: {
  order: Order
  trapIds: Set<string>
  windowDays: number
  cap: number
  compact?: boolean
  onClick?: () => void
}) {
  const trap = trapIds.has(order.id)
  const mark = catalogMark(order, trapIds, windowDays, cap)
  const flags = orderFlags(order, windowDays, cap).filter(
    (flag) => flag !== "payable" && flag !== "ineligible" && flag !== "refunded" && flag !== "cap"
  )
  const windowPct = Math.min(100, Math.round((100 * order.days_since_delivery) / Math.max(1, windowDays)))
  const overWindow = order.days_since_delivery > windowDays

  const inner = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[11px] text-muted-foreground">{order.id}</p>
          <p className="text-sm font-medium">{order.sku}</p>
          <p className="text-[12px] text-muted-foreground">
            {order.customer}
            {order.customer_id ? ` · ${order.customer_id}` : ""}
          </p>
        </div>
        <p className="font-mono text-sm tabular-nums">{moneyLabel(order.amount_eur, order.currency)}</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        <Tag tone={mark.tone} solid={mark.tone !== "slate"} title={mark.title}>
          {mark.label}
        </Tag>
        {flags.map((flag) => (
          <Tag key={flag} tone={CLAUSE_TONE[flag] ?? "slate"}>
            {flag}
          </Tag>
        ))}
      </div>
      {mark.label !== "MUST PAY" ? (
        <p className="mt-2 text-[12px] leading-snug text-muted-foreground">{mark.title}</p>
      ) : null}
      {order.shop_status ? (
        <p className="mt-3 font-mono text-[11px] text-muted-foreground">{order.shop_status}</p>
      ) : (
        <div className="mt-3">
          <div className="mb-1 flex justify-between font-mono text-[11px] text-muted-foreground">
            <span>
              {order.days_since_delivery}d / {windowDays}d window
            </span>
            <span>cap {moneyLabel(cap, order.currency)}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", overWindow ? "bg-tag-rose" : "bg-tag-green")}
              style={{ width: `${Math.min(100, overWindow ? 100 : windowPct)}%` }}
            />
          </div>
        </div>
      )}
    </>
  )

  const className = cn(
    "w-full rounded-xl border bg-card p-3 text-left",
    trap && "shadow-[inset_3px_0_0_var(--tag-rose)]",
    mark.label === "MUST PAY" && "shadow-[inset_3px_0_0_var(--tag-green)]",
    onClick && "hover:bg-accent/50",
    compact && "p-2.5"
  )

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {inner}
      </button>
    )
  }
  return <div className={className}>{inner}</div>
}
