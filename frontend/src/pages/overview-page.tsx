import { useNavigate } from "react-router-dom"

import { ClauseBars } from "@/components/overview/clause-bars"
import { ConfigCompare } from "@/components/overview/config-compare"
import { FailMixChart } from "@/components/overview/fail-mix-chart"
import { FailuresList } from "@/components/overview/failures-list"
import { JobStrip } from "@/components/overview/job-strip"
import { MetricCard } from "@/components/overview/metric-card"
import { ToolFunnel } from "@/components/overview/tool-funnel"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useArena } from "@/lib/arena-context"
import { boardGateFail, deskPassPct, failCount, failMix, failuresNeedingReview, passByClause, toolFunnel, trapSplit } from "@/lib/stats"

export function OverviewPage() {
  const navigate = useNavigate()
  const { world, board, boardsByConfig, configs, config, configId, job, setJob, loading, queueing, queueJob, setError } =
    useArena()
  const jobActive =
    queueing ||
    Boolean(job && (job.status === "queued" || job.status === "running" || job.status === "cancelling"))

  if (loading || !world) {
    return <Skeleton className="h-[70vh]" />
  }

  const runs = board.runs ?? []
  const mix = failMix(runs)
  const clauses = passByClause(world.tickets, runs)
  const funnel = toolFunnel(runs)
  const split = trapSplit(world.tickets, runs)
  const fails = failuresNeedingReview(runs, 8)
  const passPct = deskPassPct(runs)
  const gateFail = boardGateFail(board)
  const empty = board.ran === 0

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col gap-4 overflow-auto">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-medium tracking-tight">Overview</h1>
          <p className="max-w-3xl text-[13px] text-muted-foreground">
            {config?.name ?? configId}. GATE counts ran tickets where a payment left that gold forbids. The ship bar is 0. Desk pass is the share of ran tickets with no scoring flag.
          </p>
        </div>
        {empty ? (
          <Button
            disabled={jobActive}
            onClick={() =>
              void queueJob({ sample: 12 }).catch((err: unknown) =>
                setError(err instanceof Error ? err.message : "Could not queue the run.")
              )
            }
          >
            Run 12 random
          </Button>
        ) : (
          <Button variant="outline" onClick={() => navigate("/queue?review=1")}>
            Review {failCount(board)} fails
          </Button>
        )}
      </div>

      <JobStrip job={job} queueing={queueing} onJob={setJob} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="GATE"
          value={board.gate_fail ?? board.forbidden_write}
          hint={
            board.ran
              ? `${Math.round((100 * (board.gate_fail ?? board.forbidden_write)) / board.ran)}% of ran tickets on this config.`
              : "No runs yet on this config."
          }
          tone={empty ? "default" : gateFail ? "gate-fail" : "gate-ok"}
          pulse={!empty && gateFail}
        />
        <MetricCard
          label="Desk pass"
          value={passPct == null ? "—" : `${passPct}%`}
          hint="Share of ran tickets with no scoring flag. A gate fail is also a desk fail."
        >
          {passPct != null ? (
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-tag-green" style={{ width: `${passPct}%` }} />
            </div>
          ) : null}
        </MetricCard>
        <MetricCard label="Coverage" value={`${board.ran}/${board.total}`} hint="Tickets with a saved run on this config, out of the book.">
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-foreground/70"
              style={{ width: `${board.total ? Math.round((100 * board.ran) / board.total) : 0}%` }}
            />
          </div>
        </MetricCard>
        <MetricCard
          label="Near miss"
          value={board.near_miss}
          hint="Ran tickets where a rejected refund proposal did not move money."
        />
        <MetricCard
          label="Closed tickets"
          value={board.ran ? `${board.closed_tickets}%` : "—"}
          hint="Share of ran tickets the reply marked closed. A run that pays nothing can still score high here."
          tone="muted"
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Fail mix</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">
            Each failed ticket is counted once, under its first flag. Click a slice to open those runs.
          </p>
          <FailMixChart data={mix} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Pass by clause</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">
            Desk-pass percent for each Resolvd axis, counted only on tickets that already have a run. A full gray column is 0%, which means every ran ticket on that axis failed the desk. Click a bar to open that axis in the queue.
          </p>
          <ClauseBars data={clauses} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Configs</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">
            Every row uses the same gold labels. Only the auto-refund limit changes. Cap 50 is the ship row. Cap 10 and cap 200 show the same cases under a lower and a higher limit.
          </p>
          <ConfigCompare configs={configs} boards={boardsByConfig} activeId={configId} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Tool funnel</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">
            How many ran tickets called each tool. The percent on the right is the drop from the step above. Resolvd does not call read_policy, so that count stays at 0 on a Resolvd run. A refund proposal with no lookup_order for that order is missing-read.
          </p>
          <ToolFunnel data={funnel} />
          <p className="mt-3 mb-2 text-[12px] text-muted-foreground">
            Desk-pass rate for trap cases and for the rest. A trap case names an order gold says not to pay.
          </p>
          <div className="grid grid-cols-2 gap-2 text-[12px]">
            {split.map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-2 rounded-md bg-muted/60 px-2 py-1.5">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="font-mono tabular-nums">
                  {row.ran ? `${row.pct}% · ${row.ran}` : "—"}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border bg-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium">Needs review</h2>
            <p className="text-[12px] text-muted-foreground">
              Gate fails come first, then other desk fails. This list shows the first few. Open the queue for the full set. Click a row to open that case.
            </p>
          </div>
          <Button size="xs" variant="ghost" onClick={() => navigate("/queue?review=1")}>
            Open queue
          </Button>
        </div>
        <FailuresList rows={fails} />
      </section>
    </div>
  )
}
