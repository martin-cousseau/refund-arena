import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { cancelJob } from "@/lib/api"
import { resultFromScore } from "@/lib/result"
import type { ArenaJob } from "@/lib/types"
import { cn } from "cn"

function isActive(status: ArenaJob["status"]): boolean {
  return status === "queued" || status === "running" || status === "cancelling"
}

export function JobStrip({
  job,
  queueing = false,
  onJob,
}: {
  job: ArenaJob | null
  queueing?: boolean
  onJob: (job: ArenaJob) => void
}) {
  if (!job || (queueing && !isActive(job.status))) {
    if (!queueing) return null
    return (
      <div className="rounded-xl border bg-card p-3">
        <div className="mb-2 text-[12px] font-medium tracking-wide uppercase">Queuing</div>
        <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="absolute inset-y-0 w-1/3 bg-primary progress-wait" />
        </div>
      </div>
    )
  }

  const pct = job.total ? (100 * job.done) / job.total : 0
  const active = isActive(job.status)
  const waiting = active && job.done === 0

  return (
    <div className="rounded-xl border bg-card p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2 text-[12px]">
          <span className="font-medium tracking-wide uppercase">{job.status}</span>
          <span className="font-mono text-muted-foreground tabular-nums">
            {job.done}/{job.total}
          </span>
          <span className="truncate text-muted-foreground">{job.config_id}</span>
        </div>
        {active ? (
          <Button
            size="xs"
            variant="outline"
            onClick={() =>
              void cancelJob(job.id)
                .then(onJob)
                .catch(() => undefined)
            }
          >
            Cancel
          </Button>
        ) : null}
      </div>
      {waiting ? (
        <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="absolute inset-y-0 w-1/3 bg-primary progress-wait" />
        </div>
      ) : (
        <Progress value={pct} className={cn(job.status === "failed" && "*:bg-tag-rose")} />
      )}
      {job.items.length > 0 ? (
        <div className="mt-2 flex max-h-16 flex-wrap gap-0.5 overflow-hidden">
          {job.items.map((item) => {
            const kind = resultFromScore(item.score, item.status)
            return (
              <span
                key={item.ticket_id}
                title={`${item.ticket_id} ${item.title ?? ""} ${kind}`}
                className={cn(
                  "size-1.5 rounded-[1px]",
                  kind === "running" && "bg-tag-green pulse-run",
                  kind === "pass" && "bg-tag-green",
                  kind === "gate" && "bg-tag-rose",
                  kind === "desk" && "bg-tag-amber",
                  kind === "error" && "bg-tag-rose",
                  (kind === "unrun" || item.status === "queued") && "bg-muted-foreground/25",
                  item.status === "cancelled" && "bg-muted-foreground/40"
                )}
              />
            )
          })}
        </div>
      ) : null}
      {job.error ? <p className="mt-2 text-[12px] text-tag-rose">{job.error}</p> : null}
    </div>
  )
}
