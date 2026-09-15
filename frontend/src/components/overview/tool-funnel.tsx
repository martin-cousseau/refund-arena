import type { FunnelStep } from "@/lib/stats"
import { cn } from "cn"

export function ToolFunnel({ data }: { data: FunnelStep[] }) {
  const max = Math.max(1, ...data.map((row) => row.count))
  return (
    <div className="flex h-[220px] flex-col justify-center gap-3">
      {data.map((row, index) => {
        const prev = index === 0 ? row.count : data[index - 1].count
        const drop = prev === 0 ? 0 : Math.round((100 * (prev - row.count)) / prev)
        return (
          <div key={row.step} className="flex items-center gap-3">
            <div className="w-28 shrink-0 font-mono text-[11px] text-muted-foreground">{row.step}</div>
            <div className="h-7 min-w-0 flex-1 rounded-md bg-muted">
              <div
                className={cn("flex h-full items-center rounded-md bg-tag-violet/80 px-2 text-[11px] font-medium text-white")}
                style={{ width: `${Math.max(8, (100 * row.count) / max)}%` }}
              >
                {row.count}
              </div>
            </div>
            {index > 0 ? (
              <div className="w-14 shrink-0 text-right font-mono text-[11px] text-muted-foreground tabular-nums">
                {drop ? `−${drop}%` : "0%"}
              </div>
            ) : (
              <div className="w-14" />
            )}
          </div>
        )
      })}
    </div>
  )
}
