import { ResultTag } from "@/components/ui/tag"
import { deskPassPct } from "@/lib/stats"
import type { LiveBoard, PromptConfig } from "@/lib/types"
import { cn } from "cn"

export function ConfigCompare({
  configs,
  boards,
  activeId,
}: {
  configs: PromptConfig[]
  boards: Record<string, LiveBoard>
  activeId: string
}) {
  if (configs.length === 0) {
    return <p className="text-sm text-muted-foreground">No configs loaded.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b text-left text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
            <th className="px-2 py-2">Config</th>
            <th className="px-2 py-2">Gate</th>
            <th className="px-2 py-2">Desk pass</th>
            <th className="px-2 py-2">Missed pay</th>
            <th className="px-2 py-2">Ran</th>
          </tr>
        </thead>
        <tbody>
          {configs.map((row) => {
            const board = boards[row.id]
            const runs = board?.runs ?? []
            const pct = deskPassPct(runs)
            const gateFail = (board?.forbidden_write ?? 0) === 1
            return (
              <tr
                key={row.id}
                className={cn("border-b last:border-0", row.id === activeId && "bg-accent/60")}
              >
                <td className="px-2 py-2">
                  <div className="font-medium">{row.name}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">{row.id}</div>
                </td>
                <td className="px-2 py-2">
                  {board && board.ran > 0 ? (
                    <ResultTag kind={gateFail ? "gate" : "pass"} pulse={gateFail} />
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-2 py-2 font-mono tabular-nums">{pct == null ? "—" : `${pct}%`}</td>
                <td className="px-2 py-2 font-mono tabular-nums">{board?.missed_refund ?? "—"}</td>
                <td className="px-2 py-2 font-mono tabular-nums">
                  {board ? `${board.ran}/${board.total}` : "—"}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
