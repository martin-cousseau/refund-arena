import { Tag } from "@/components/ui/tag"
import { CLAUSE_TONE } from "@/lib/clauses"
import { isMustPay, orderFlags } from "@/lib/orders"
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
  const must = isMustPay(order, trapIds, windowDays, cap)
  const flags = orderFlags(order, trapIds, windowDays, cap).filter((flag) => flag !== "trap" && flag !== "eligible")
  const windowPct = Math.min(100, Math.round((100 * order.days_since_delivery) / Math.max(1, windowDays)))
  const overWindow = order.days_since_delivery > windowDays

  const inner = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[11px] text-muted-foreground">{order.id}</p>
          <p className="text-sm font-medium">{order.sku}</p>
          <p className="text-[12px] text-muted-foreground">{order.customer}</p>
        </div>
        <p className="font-mono text-sm tabular-nums">€{order.amount_eur}</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {must ? (
          <Tag tone="green" solid>
            MUST PAY
          </Tag>
        ) : trap ? (
          <Tag tone="rose" solid>
            TRAP
          </Tag>
        ) : (
          <Tag tone="slate">order</Tag>
        )}
        {flags.map((flag) => (
          <Tag key={flag} tone={CLAUSE_TONE[flag] ?? "slate"}>
            {flag}
          </Tag>
        ))}
      </div>
      <div className="mt-3">
        <div className="mb-1 flex justify-between font-mono text-[11px] text-muted-foreground">
          <span>
            {order.days_since_delivery}d / {windowDays}d window
          </span>
          <span>cap €{cap}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full", overWindow ? "bg-tag-rose" : "bg-tag-green")}
            style={{ width: `${Math.min(100, overWindow ? 100 : windowPct)}%` }}
          />
        </div>
      </div>
    </>
  )

  const className = cn(
    "w-full rounded-xl border bg-card p-3 text-left",
    trap && "shadow-[inset_3px_0_0_var(--tag-rose)]",
    must && "shadow-[inset_3px_0_0_var(--tag-green)]",
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
