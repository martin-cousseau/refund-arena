import { useNavigate } from "react-router-dom"

import { ResultTag } from "@/components/ui/tag"
import type { FailureRow } from "@/lib/stats"

export function FailuresList({ rows }: { rows: FailureRow[] }) {
  const navigate = useNavigate()

  if (rows.length === 0) {
    return <p className="py-6 text-sm text-muted-foreground">No tickets need review on this config.</p>
  }

  return (
    <ul className="divide-y">
      {rows.map((row) => (
        <li key={row.ticket_id}>
          <button
            type="button"
            onClick={() => navigate(`/queue/${row.ticket_id}`)}
            className="flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-muted/60"
          >
            <span className="w-12 shrink-0 font-mono text-[11px] text-muted-foreground">{row.ticket_id}</span>
            <span className="min-w-0 flex-1 truncate text-[13px]">{row.title}</span>
            <span className="hidden min-w-0 max-w-[40%] truncate font-mono text-[11px] text-muted-foreground sm:block">
              {row.reason}
            </span>
            <ResultTag kind={row.kind} />
          </button>
        </li>
      ))}
    </ul>
  )
}
