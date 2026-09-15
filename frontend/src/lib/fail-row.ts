import { cn } from "cn"

import type { ResultKind } from "@/lib/result"

export function failRowClass(kind: ResultKind, selected: boolean): string {
  return cn(
    "border-transparent",
    kind === "gate" && "bg-tag-rose/8 shadow-[inset_3px_0_0_var(--tag-rose)]",
    kind === "desk" && "bg-tag-amber/10 shadow-[inset_3px_0_0_var(--tag-amber)]",
    kind === "error" && "bg-tag-rose/8 shadow-[inset_3px_0_0_var(--tag-rose)]",
    selected && "bg-accent",
    selected && kind === "gate" && "bg-tag-rose/14",
    selected && kind === "desk" && "bg-tag-amber/16"
  )
}
