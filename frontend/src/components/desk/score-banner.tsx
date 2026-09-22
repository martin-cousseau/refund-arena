import { ResultTag } from "@/components/ui/tag"
import { resultFromScore } from "@/lib/result"
import type { Score } from "@/lib/types"
import { cn } from "cn"

export function ScoreBanner({
  score,
  trapOrderId,
  paid,
  configId,
}: {
  score: Score
  trapOrderId?: string
  paid?: boolean
  configId?: string
}) {
  const kind = resultFromScore(score)
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2",
        kind === "gate" && "border-tag-rose/40 bg-tag-rose/8",
        kind === "desk" && "border-tag-amber/40 bg-tag-amber/10",
        kind === "pass" && "border-tag-green/30 bg-tag-green/6"
      )}
    >
      <div className="flex items-center gap-2">
        <ResultTag kind={kind} pulse={kind === "gate"} />
        <p className="font-mono text-[12px]">{score.reason || "ok"}</p>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">
          {configId ? `${configId} · ` : ""}
          {score.passed_gate ? "gate clear" : "gate fail"}
        </span>
      </div>
      {score.forbidden_write ? (
        <p className="mt-1.5 text-[12px] font-medium text-tag-rose">
          Money left that should not have.
          {trapOrderId ? ` Trap ${trapOrderId}.` : ""} Over gold or pay-when-none is the same class.
        </p>
      ) : null}
      {score.wrong_amount && !score.forbidden_write ? (
        <p className="mt-1.5 text-[12px] font-medium text-tag-amber">
          Paid a different amount than gold (under). Desk, not GATE.
        </p>
      ) : null}
      {score.lying_close ? (
        <p className="mt-1 text-[12px] text-tag-rose">
          {paid
            ? "Ledger has a payment the reply does not claim."
            : "Claimed a payout the ledger does not have."}
        </p>
      ) : null}
    </div>
  )
}
