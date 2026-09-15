import type { ComponentProps } from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

import type { TagTone } from "@/lib/clauses"

const tagVariants = cva(
  "inline-flex h-5 max-w-full shrink-0 items-center gap-1 truncate rounded px-1.5 text-[11px] leading-none font-medium tracking-wide whitespace-nowrap",
  {
    variants: {
      tone: {
        rose: "bg-tag-rose/12 text-tag-rose",
        green: "bg-tag-green/12 text-tag-green",
        amber: "bg-tag-amber/12 text-tag-amber",
        sky: "bg-tag-sky/12 text-tag-sky",
        violet: "bg-tag-violet/12 text-tag-violet",
        orange: "bg-tag-orange/12 text-tag-orange",
        pink: "bg-tag-pink/12 text-tag-pink",
        indigo: "bg-tag-indigo/12 text-tag-indigo",
        teal: "bg-tag-teal/12 text-tag-teal",
        lime: "bg-tag-lime/14 text-tag-lime",
        slate: "bg-muted text-muted-foreground",
      },
      solid: {
        true: "",
        false: "",
      },
    },
    compoundVariants: [
      { tone: "rose", solid: true, class: "bg-tag-rose text-white" },
      { tone: "green", solid: true, class: "bg-tag-green text-white dark:text-background" },
      { tone: "amber", solid: true, class: "bg-tag-amber text-white" },
      { tone: "sky", solid: true, class: "bg-tag-sky text-white" },
      { tone: "violet", solid: true, class: "bg-tag-violet text-white" },
      { tone: "orange", solid: true, class: "bg-tag-orange text-white" },
      { tone: "pink", solid: true, class: "bg-tag-pink text-white" },
      { tone: "indigo", solid: true, class: "bg-tag-indigo text-white" },
      { tone: "teal", solid: true, class: "bg-tag-teal text-white" },
      { tone: "lime", solid: true, class: "bg-tag-lime text-white" },
      { tone: "slate", solid: true, class: "bg-foreground text-background" },
    ],
    defaultVariants: {
      tone: "slate",
      solid: false,
    },
  }
)

export function Tag({
  className,
  tone,
  solid,
  pulse,
  children,
  ...props
}: ComponentProps<"span"> &
  VariantProps<typeof tagVariants> & {
    tone?: TagTone
    pulse?: boolean
  }) {
  return (
    <span className={cn(tagVariants({ tone, solid }), pulse && "pulse-fail", className)} {...props}>
      {children}
    </span>
  )
}

export function ResultTag({
  kind,
  pulse,
}: {
  kind: "unrun" | "running" | "pass" | "desk" | "gate" | "error"
  pulse?: boolean
}) {
  if (kind === "unrun") return null
  if (kind === "running") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-tag-green">
        <span className="size-1.5 rounded-full bg-tag-green pulse-run" />
        RUNNING
      </span>
    )
  }
  if (kind === "gate") {
    return (
      <Tag tone="rose" solid pulse={pulse}>
        GATE
      </Tag>
    )
  }
  if (kind === "desk") {
    return (
      <Tag tone="amber" solid>
        DESK FAIL
      </Tag>
    )
  }
  if (kind === "error") {
    return (
      <Tag tone="rose" solid>
        ERROR
      </Tag>
    )
  }
  return (
    <Tag tone="green" className="border border-tag-green/30 bg-transparent">
      PASS
    </Tag>
  )
}

export { tagVariants }
