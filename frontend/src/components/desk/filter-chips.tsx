import type { ReactNode } from "react"

import { CLAUSE_TONE, CLAUSES } from "@/lib/clauses"
import { cn } from "cn"

export function FilterChips({
  clause,
  onClause,
  traps,
  onTraps,
  review,
  onReview,
  unrun,
  onUnrun,
}: {
  clause: string
  onClause: (value: string) => void
  traps: boolean
  onTraps: (value: boolean) => void
  review: boolean
  onReview: (value: boolean) => void
  unrun: boolean
  onUnrun: (value: boolean) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <Chip active={clause === "all"} onClick={() => onClause("all")}>
        all
      </Chip>
      {CLAUSES.map((item) => (
        <Chip key={item} active={clause === item} onClick={() => onClause(item)} tone={CLAUSE_TONE[item]}>
          {item}
        </Chip>
      ))}
      <span className="mx-1 h-4 w-px bg-border" />
      <Chip active={review} onClick={() => onReview(!review)} tone="rose">
        needs review
      </Chip>
      <Chip active={traps} onClick={() => onTraps(!traps)} tone="rose">
        traps
      </Chip>
      <Chip active={unrun} onClick={() => onUnrun(!unrun)}>
        unrun
      </Chip>
    </div>
  )
}

function Chip({
  active,
  onClick,
  children,
  tone,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
  tone?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "h-6 rounded-md border px-2 text-[11px] font-medium capitalize",
        active ? "border-transparent text-foreground" : "border-transparent bg-transparent text-muted-foreground hover:bg-muted"
      )}
      style={
        active && tone
          ? { background: `color-mix(in oklch, var(--tag-${tone}) 16%, transparent)`, color: `var(--tag-${tone})` }
          : active
            ? { background: "var(--accent)" }
            : undefined
      }
    >
      {children}
    </button>
  )
}
