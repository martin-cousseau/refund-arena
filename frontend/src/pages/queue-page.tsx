import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"

import { FilterChips } from "@/components/desk/filter-chips"
import { TicketList, type ListedTicket } from "@/components/desk/ticket-list"
import { TicketProperties, TicketWorkspace } from "@/components/desk/ticket-workspace"
import { JobStrip } from "@/components/overview/job-strip"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { useMediaQuery } from "@/hooks/use-media-query"
import { runTicket } from "@/lib/api"
import { useArena } from "@/lib/arena-context"
import { CLAUSES } from "@/lib/clauses"
import { resultFromScore, type ResultKind } from "@/lib/result"
import type { Ticket } from "@/lib/types"

function rank(kind: ResultKind): number {
  if (kind === "gate") return 0
  if (kind === "desk") return 1
  if (kind === "error") return 2
  if (kind === "running") return 3
  if (kind === "unrun") return 4
  return 5
}

export function QueuePage() {
  const { ticketId } = useParams()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const desktop = useMediaQuery("(min-width: 1024px)")
  const { world, configId, board, runsByTicket, job, setJob, setBoard, setRun, setError, loading, queueJob } =
    useArena()

  const [query, setQuery] = useState("")
  const [sample, setSample] = useState(12)
  const [concurrency, setConcurrency] = useState(4)
  const [confirmAll, setConfirmAll] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const clause = params.get("clause") && CLAUSES.includes(params.get("clause") as (typeof CLAUSES)[number])
    ? params.get("clause")!
    : "all"
  const traps = params.get("traps") === "1"
  const review = params.get("review") === "1"
  const unrun = params.get("unrun") === "1"
  const orderFilter = params.get("order")

  const tickets = useMemo(() => world?.tickets ?? [], [world])
  const trapIds = useMemo(() => new Set(world?.trap_order_ids ?? []), [world])

  const setFilter = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(params)
      if (!value || value === "all" || value === "0") next.delete(key)
      else next.set(key, value)
      setParams(next, { replace: true })
    },
    [params, setParams]
  )

  const listed: ListedTicket[] = useMemo(() => {
    const q = query.trim().toLowerCase()
    const running = new Set(
      (job?.items ?? []).filter((item) => item.status === "running" || item.status === "queued").map((item) => item.ticket_id)
    )
    const rows = tickets
      .filter((row) => {
        if (clause !== "all" && row.clause !== clause) return false
        if (traps && !row.trap) return false
        if (orderFilter && row.gold_order_id !== orderFilter && row.forbidden_order_id !== orderFilter) return false
        if (q && !`${row.id} ${row.title} ${row.message} ${row.clause}`.toLowerCase().includes(q)) return false
        const persisted = runsByTicket[row.id] ?? board.runs?.find((item) => item.ticket_id === row.id)
        const kind = running.has(row.id)
          ? "running"
          : resultFromScore(persisted && "score" in persisted ? persisted.score : null)
        if (review && kind !== "gate" && kind !== "desk" && kind !== "error") return false
        if (unrun && kind !== "unrun") return false
        return true
      })
      .map((ticket) => {
        const jobItem = job?.items.find((item) => item.ticket_id === ticket.id)
        const persisted = runsByTicket[ticket.id] ?? board.runs?.find((item) => item.ticket_id === ticket.id)
        const runningNow = jobItem?.status === "running" || runningId === ticket.id
        const result = resultFromScore(jobItem?.score ?? persisted?.score, runningNow ? "running" : jobItem?.status)
        return { ticket, result, running: runningNow }
      })
    rows.sort((a, b) => rank(a.result) - rank(b.result) || a.ticket.id.localeCompare(b.ticket.id))
    return rows
  }, [board.runs, clause, job, orderFilter, query, review, runningId, runsByTicket, tickets, traps, unrun])

  const selectedId = ticketId ?? listed[0]?.ticket.id ?? tickets[0]?.id ?? null
  const selected: Ticket | null = tickets.find((row) => row.id === selectedId) ?? null
  const selectedRun = selected
    ? (runsByTicket[selected.id] ?? null)
    : null
  const jobActive = Boolean(job && (job.status === "queued" || job.status === "running" || job.status === "cancelling"))

  const selectTicket = useCallback(
    (id: string) => {
      navigate({ pathname: `/queue/${id}`, search: params.toString() })
    },
    [navigate, params]
  )

  const handleRunOne = useCallback(
    async (id: string) => {
      setError(null)
      setRunningId(id)
      try {
        const payload = await runTicket(id, configId)
        setRun(payload)
        if (payload.board) setBoard(payload.board)
      } catch (err) {
        setError(err instanceof Error ? err.message : `Run ${id} failed.`)
      } finally {
        setRunningId(null)
      }
    },
    [configId, setBoard, setError, setRun]
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        if (event.key === "Escape") (target as HTMLInputElement).blur()
        return
      }
      if (event.key === "/") {
        event.preventDefault()
        searchRef.current?.focus()
        return
      }
      if (event.key === "f") {
        event.preventDefault()
        setFilter("review", review ? null : "1")
        return
      }
      if (event.key === "j" || event.key === "k") {
        event.preventDefault()
        const ids = listed.map((row) => row.ticket.id)
        const index = selectedId ? ids.indexOf(selectedId) : 0
        const next = event.key === "j" ? Math.min(ids.length - 1, index + 1) : Math.max(0, index - 1)
        if (ids[next]) selectTicket(ids[next])
        return
      }
      if (event.key === "Enter" && selected && !jobActive && !runningId) {
        event.preventDefault()
        void handleRunOne(selected.id)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [handleRunOne, jobActive, listed, review, runningId, selectTicket, selected, selectedId, setFilter])

  if (loading || !world) {
    return <Skeleton className="h-[70vh]" />
  }

  const listPane = (
    <div className="flex h-full min-h-0 w-full flex-col gap-2 lg:w-[320px] lg:shrink-0">
      <Input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search id, subject, body  /" />
      <FilterChips
        clause={clause}
        onClause={(value) => setFilter("clause", value)}
        traps={traps}
        onTraps={(value) => setFilter("traps", value ? "1" : null)}
        review={review}
        onReview={(value) => setFilter("review", value ? "1" : null)}
        unrun={unrun}
        onUnrun={(value) => setFilter("unrun", value ? "1" : null)}
      />
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label htmlFor="sample">Random N</Label>
          <Input
            id="sample"
            type="number"
            min={1}
            max={tickets.length}
            value={sample}
            onChange={(event) => setSample(Number(event.target.value) || 1)}
          />
        </div>
        <div>
          <Label htmlFor="conc">Workers</Label>
          <Input
            id="conc"
            type="number"
            min={1}
            max={8}
            value={concurrency}
            onChange={(event) => setConcurrency(Math.min(8, Math.max(1, Number(event.target.value) || 4)))}
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          className="min-w-0 flex-1"
          disabled={jobActive}
          onClick={() =>
            void queueJob({ sample, concurrency }).catch((err: unknown) =>
              setError(err instanceof Error ? err.message : "Could not queue the run.")
            )
          }
        >
          Run {sample} random
        </Button>
        <Button size="sm" variant="outline" className="shrink-0" disabled={jobActive} onClick={() => setConfirmAll(true)}>
          Run all
        </Button>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {listed.length} of {tickets.length}
        {orderFilter ? ` · order ${orderFilter}` : ""} · j/k move · enter run · f review
      </p>
      <TicketList
        rows={listed}
        selectedId={selectedId}
        onSelect={selectTicket}
        pulseGate={jobActive && board.forbidden_write === 1}
      />
    </div>
  )

  const detail = selected ? (
    <>
      <TicketWorkspace
        ticket={selected}
        run={selectedRun}
        running={runningId === selected.id}
        busy={Boolean(runningId) || jobActive}
        onRun={() => void handleRunOne(selected.id)}
        trapIds={trapIds}
      />
      <div className="hidden h-full w-[280px] shrink-0 overflow-hidden rounded-xl border bg-card lg:block">
        <TicketProperties
          ticket={selected}
          run={selectedRun}
          orders={world.orders}
          trapIds={trapIds}
          windowDays={world.refund_window_days}
          cap={world.amount_cap_eur}
        />
      </div>
    </>
  ) : (
    <div className="flex flex-1 items-center justify-center rounded-xl border text-sm text-muted-foreground">
      Select a ticket.
    </div>
  )

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {job ? <JobStrip job={job} onJob={setJob} /> : null}
      <div className="flex min-h-0 flex-1 gap-3">
        {listPane}
        {desktop ? detail : null}
      </div>

      {!desktop && selected ? (
        <Sheet open={Boolean(ticketId)} onOpenChange={(open) => !open && navigate({ pathname: "/queue", search: params.toString() })}>
          <SheetContent side="right" className="w-full pt-12 sm:max-w-lg" showCloseButton>
            <div className="flex h-full min-h-0 flex-col gap-3 overflow-auto p-3">
              <TicketWorkspace
                ticket={selected}
                run={selectedRun}
                running={runningId === selected.id}
                busy={Boolean(runningId) || jobActive}
                onRun={() => void handleRunOne(selected.id)}
                trapIds={trapIds}
                className="h-[62svh] flex-none"
              />
              <TicketProperties
                ticket={selected}
                run={selectedRun}
                orders={world.orders}
                trapIds={trapIds}
                windowDays={world.refund_window_days}
                cap={world.amount_cap_eur}
              />
            </div>
          </SheetContent>
        </Sheet>
      ) : null}

      <Dialog open={confirmAll} onOpenChange={setConfirmAll}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run all {tickets.length} tickets</DialogTitle>
            <DialogDescription>
              Queues every ticket under {configId} with {concurrency} parallel workers. Each call hits the model.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmAll(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                setConfirmAll(false)
                void queueJob({ all: true, concurrency }).catch((err: unknown) =>
                  setError(err instanceof Error ? err.message : "Could not queue the run.")
                )
              }}
            >
              Queue full run
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
