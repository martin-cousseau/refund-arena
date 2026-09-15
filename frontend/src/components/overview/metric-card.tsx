import type { ReactNode } from "react"
import { cn } from "cn"

export function MetricCard({
  label,
  value,
  hint,
  tone = "default",
  pulse,
  children,
}: {
  label: string
  value: string | number
  hint?: string
  tone?: "default" | "gate-ok" | "gate-fail" | "muted"
  pulse?: boolean
  children?: ReactNode
}) {
  return (
    <div
      className={cn(
        "flex min-h-[112px] flex-col justify-between rounded-xl border bg-card p-4",
        tone === "gate-ok" && "border-tag-green/40 bg-tag-green/6",
        tone === "gate-fail" && "border-tag-rose/50 bg-tag-rose/8",
        tone === "muted" && "bg-muted/40"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        {pulse ? <span className="size-2 rounded-full bg-tag-rose pulse-fail" /> : null}
      </div>
      <p
        className={cn(
          "font-heading text-[2rem] leading-none font-medium tracking-tight tabular-nums",
          tone === "gate-ok" && "text-tag-green",
          tone === "gate-fail" && "text-tag-rose pulse-fail",
          tone === "muted" && "text-muted-foreground"
        )}
      >
        {value}
      </p>
      {hint ? <p className="text-[11px] text-muted-foreground">{hint}</p> : null}
      {children}
    </div>
  )
}
