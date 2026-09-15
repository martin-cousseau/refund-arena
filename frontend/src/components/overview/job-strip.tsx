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
  onJob,
}: {
  job: ArenaJob
  onJob: (job: ArenaJob) => void
}) {
  const pct = job.total ? Math.round((100 * job.done) / job.total) : 0
  const active = isActive(job.status)

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
      <Progress value={pct} className={cn(job.status === "failed" && "*:bg-tag-rose")} />
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
