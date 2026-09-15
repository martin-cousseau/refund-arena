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
import { deskPassPct, failCount, failMix, failuresNeedingReview, passByClause, toolFunnel, trapSplit } from "@/lib/stats"

export function OverviewPage() {
  const navigate = useNavigate()
  const { world, board, boardsByConfig, configs, config, configId, job, setJob, loading, queueJob, setError } =
    useArena()

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
  const gateFail = board.forbidden_write === 1
  const empty = board.ran === 0

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col gap-4 overflow-auto">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-medium tracking-tight">Overview</h1>
          <p className="text-[13px] text-muted-foreground">
            {config?.name ?? configId} · closed-tickets is vanity · forbidden-write is the ship gate
          </p>
        </div>
        {empty ? (
          <Button
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

      {job ? <JobStrip job={job} onJob={setJob} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Forbidden write"
          value={board.forbidden_write}
          hint={`ship gate · ${config?.name ?? configId}`}
          tone={empty ? "default" : gateFail ? "gate-fail" : "gate-ok"}
          pulse={!empty && gateFail}
        />
        <MetricCard
          label="Desk pass"
          value={passPct == null ? "—" : `${passPct}%`}
          hint="utility, not vanity"
        >
          {passPct != null ? (
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-tag-green" style={{ width: `${passPct}%` }} />
            </div>
          ) : null}
        </MetricCard>
        <MetricCard label="Coverage" value={`${board.ran}/${board.total}`} hint="this config">
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-foreground/70"
              style={{ width: `${board.total ? Math.round((100 * board.ran) / board.total) : 0}%` }}
            />
          </div>
        </MetricCard>
        <MetricCard
          label="Closed tickets"
          value={board.closed_tickets}
          hint="vanity · a mute agent can look healthy here"
          tone="muted"
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Fail mix</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">Primary flag per ticket. Click a slice to open Runs.</p>
          <FailMixChart data={mix} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Pass by clause</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">Desk pass % on tickets that have been run. Click a bar for Queue.</p>
          <ClauseBars data={clauses} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Configs</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">Same gold. Naive and Policy are diagnostic. Production is the ship candidate.</p>
          <ConfigCompare configs={configs} boards={boardsByConfig} activeId={configId} />
        </section>
        <section className="rounded-xl border bg-card p-4">
          <h2 className="text-sm font-medium">Tool funnel</h2>
          <p className="mb-2 text-[12px] text-muted-foreground">lookup → policy → write. A refund without the first two is missing-read.</p>
          <ToolFunnel data={funnel} />
          <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
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
            <p className="text-[12px] text-muted-foreground">Gate fails first. Click a row to open the ticket.</p>
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
