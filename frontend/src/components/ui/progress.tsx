import { cn } from "cn"

function Progress({
  value = 0,
  className,
}: {
  value?: number
  className?: string
}) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div
      data-slot="progress"
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className="h-full bg-primary transition-[width] duration-300"
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

export { Progress }
