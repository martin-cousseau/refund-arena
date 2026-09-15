import { useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"

import { TicketTags } from "@/components/desk/ticket-tags"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ResultTag, Tag } from "@/components/ui/tag"
import { resetRuns } from "@/lib/api"
import { useArena } from "@/lib/arena-context"
import { CLAUSE_TONE, goldLabel } from "@/lib/clauses"
import { failRowClass } from "@/lib/fail-row"
import { FAIL_FLAGS, activeFlags, resultFromScore, type FailFlagKey } from "@/lib/result"
import { cn } from "cn"

export function RunsPage() {
  const { board, config, configId, world, setBoard, setError, refreshRuns } = useArena()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [confirm, setConfirm] = useState(false)

  const fail = params.get("fail")
  const byId = useMemo(() => new Map((world?.tickets ?? []).map((row) => [row.id, row])), [world])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const runs = board.runs ?? []
    return runs
      .filter((row) => {
        if (fail && !row.score[fail as FailFlagKey]) return false
        if (!q) return true
        const ticket = byId.get(row.ticket_id)
        return `${row.ticket_id} ${row.title ?? ""} ${ticket?.clause ?? ""} ${row.score.reason}`.toLowerCase().includes(q)
      })
      .map((row) => {
        const ticket = byId.get(row.ticket_id)
        const kind = resultFromScore(row.score)
        return { row, ticket, kind }
      })
      .sort((a, b) => {
        const rank = (kind: string) => (kind === "gate" ? 0 : kind === "desk" ? 1 : kind === "pass" ? 2 : 3)
        return rank(a.kind) - rank(b.kind) || a.row.ticket_id.localeCompare(b.row.ticket_id)
      })
  }, [board.runs, byId, fail, query])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-medium tracking-tight">Runs</h1>
          <p className="text-[13px] text-muted-foreground">
            {config?.name ?? configId} · latest run per ticket · fails sort first
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setConfirm(true)}>
          Reset this config
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[12px] tabular-nums text-muted-foreground">
          {board.ran}/{board.total} ran
        </span>
        <span className={cn("font-mono text-[12px] tabular-nums", board.forbidden_write ? "text-tag-rose" : "text-tag-green")}>
          gate {board.forbidden_write}
        </span>
        <span className="font-mono text-[12px] tabular-nums text-muted-foreground">missed-refund {board.missed_refund}</span>
        <span className="font-mono text-[12px] tabular-nums text-muted-foreground">missed-esc {board.missed_escalate}</span>
        <span className="font-mono text-[12px] tabular-nums text-muted-foreground">wrong-amt {board.wrong_amount}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="max-w-xs"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter runs"
        />
        <Button
          size="xs"
          variant={fail ? "outline" : "default"}
          onClick={() => {
            const next = new URLSearchParams(params)
            next.delete("fail")
            setParams(next, { replace: true })
          }}
        >
          all flags
        </Button>
        {FAIL_FLAGS.map((row) => (
          <button
            key={row.key}
            type="button"
            onClick={() => {
              const next = new URLSearchParams(params)
              next.set("fail", row.key)
              setParams(next, { replace: true })
            }}
          >
            <Tag tone={fail === row.key ? "rose" : "slate"} solid={fail === row.key}>
              {row.label}
            </Tag>
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-auto rounded-xl border bg-card">
        {rows.length === 0 ? (
          <p className="p-6 text-sm text-muted-foreground">No persisted runs yet. Queue tickets from Overview or Queue.</p>
        ) : (
          <Table>
            <TableHeader className="sticky top-0 bg-card">
              <TableRow>
                <TableHead>Result</TableHead>
                <TableHead>Id</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Clause</TableHead>
                <TableHead>Gold</TableHead>
                <TableHead>Tools</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map(({ row, ticket, kind }) => (
                <TableRow
                  key={row.ticket_id}
                  className={cn("cursor-pointer", failRowClass(kind, false))}
                  onClick={() => navigate(`/queue/${row.ticket_id}`)}
                >
                  <TableCell>
                    <ResultTag kind={kind} />
                  </TableCell>
                  <TableCell className="font-mono">{row.ticket_id}</TableCell>
                  <TableCell className="max-w-[220px] truncate">{row.title}</TableCell>
                  <TableCell>
                    {ticket ? <TicketTags ticket={ticket} /> : <Tag tone={CLAUSE_TONE.info}>—</Tag>}
                  </TableCell>
                  <TableCell className="font-mono text-[11px]">
                    {ticket ? goldLabel(ticket.gold_write, ticket.gold_amount_eur, ticket.gold_order_id) : "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex max-w-[180px] flex-wrap gap-0.5">
                      {row.tools.map((tool, index) => (
                        <Tag key={`${tool}-${index}`} tone="slate">
                          {tool}
                        </Tag>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate font-mono text-[11px]" title={row.score.reason}>
                    {row.score.reason}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-0.5">
                      {activeFlags(row.score).map((flag) => (
                        <Tag key={flag} tone={flag === "forbidden_write" ? "rose" : "amber"}>
                          {flag.replaceAll("_", "-")}
                        </Tag>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset runs for {config?.name ?? configId}</DialogTitle>
            <DialogDescription>Drops persisted scores for this config only. Other configs stay.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setConfirm(false)
                void resetRuns(configId)
                  .then(setBoard)
                  .then(() => refreshRuns())
                  .catch((err: unknown) => setError(err instanceof Error ? err.message : "Reset failed."))
              }}
            >
              Reset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
