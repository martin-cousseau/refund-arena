import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tag } from "@/components/ui/tag"
import { Input } from "@/components/ui/input"
import { useArena } from "@/lib/arena-context"
import { CLAUSE_TONE } from "@/lib/clauses"
import { isMustPay, orderFlags } from "@/lib/orders"
import { cn } from "cn"

export function ShopPage() {
  const { world, loading } = useArena()
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  if (loading || !world) {
    return <Skeleton className="h-[60vh]" />
  }
  const traps = new Set(world.trap_order_ids)
  const payable = world.orders.filter((row) => isMustPay(row, traps, world.refund_window_days, world.amount_cap_eur)).length
  const q = query.trim().toLowerCase()
  const rows = world.orders.filter((row) => {
    if (!q) return true
    return `${row.id} ${row.sku} ${row.customer} ${row.pair_id ?? ""}`.toLowerCase().includes(q)
  })

  return (
    <div className="mx-auto h-full max-w-5xl overflow-auto">
      <div className="mb-4">
        <h1 className="text-lg font-medium tracking-tight">North & Co</h1>
        <p className="text-[13px] text-muted-foreground">
          {world.orders.length} orders · {payable} payable on the row · {traps.size} ineligible rows. Close pairs: day
          14/15, €150/€151, tags on/off, same SKU different customer. Window {world.refund_window_days}d · cap €
          {world.amount_cap_eur}. Ownership is not an order flag. It is the caller.
        </p>
      </div>
      <Tabs defaultValue="orders">
        <TabsList>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="policy">Policy</TabsTrigger>
          <TabsTrigger value="ledger">Seed ledger</TabsTrigger>
        </TabsList>
        <TabsContent value="orders" className="mt-4">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter id, SKU, customer, pair"
            className="mb-3 max-w-sm"
          />
          <div className="rounded-xl border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead className="text-right">Days</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Flags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => {
                  const must = isMustPay(row, traps, world.refund_window_days, world.amount_cap_eur)
                  const trap = traps.has(row.id)
                  const flags = orderFlags(row, traps, world.refund_window_days, world.amount_cap_eur).filter(
                    (flag) => flag !== "payable" && flag !== "ineligible"
                  )
                  return (
                    <TableRow
                      key={row.id}
                      className={cn("cursor-pointer", trap && "bg-tag-rose/5", must && "bg-tag-green/5")}
                      onClick={() => navigate(`/queue?order=${row.id}`)}
                    >
                      <TableCell className="font-mono text-[12px]">{row.id}</TableCell>
                      <TableCell>
                        <div>
                          <p className="text-[13px]">{row.sku}</p>
                          {row.pair_id ? (
                            <p className="font-mono text-[11px] text-muted-foreground">
                              {row.pair_id} · {row.pair_role}
                            </p>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="text-[13px]">
                        <div>{row.customer}</div>
                        {row.customer_id ? (
                          <p className="font-mono text-[11px] text-muted-foreground">{row.customer_id}</p>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-right font-mono text-[12px]">{row.days_since_delivery}</TableCell>
                      <TableCell className="text-right font-mono text-[12px]">€{row.amount_eur}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {must ? (
                            <Tag tone="green" solid>
                              MUST PAY
                            </Tag>
                          ) : trap ? (
                            <Tag tone="rose" solid>
                              TRAP
                            </Tag>
                          ) : (
                            <Tag tone="slate">order</Tag>
                          )}
                          {flags.map((flag) => (
                            <Tag key={flag} tone={CLAUSE_TONE[flag] ?? "slate"}>
                              {flag}
                            </Tag>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
        <TabsContent value="policy" className="mt-4">
          <div className="mb-3 rounded-xl border bg-card p-4 text-[13px]">
            <p className="font-medium">Refund service</p>
            <p className="mt-1 text-muted-foreground">
              Checks {(world.service?.checks ?? []).join(", ") || "the row"}. Does not check{" "}
              {(world.service?.does_not_check ?? []).join(", ") || "nothing"}. The Policy prompt inlines current pages
              only. The archive is available through read_policy.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            {(world.policy_pages ?? []).map((page) => (
              <section key={page.id} className="rounded-xl border bg-card p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-medium">{page.title}</h3>
                  <Tag tone={page.status === "current" ? "green" : "amber"}>{page.status}</Tag>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {page.id} · {page.updated}
                  </span>
                </div>
                <p className="text-[13px] leading-relaxed whitespace-pre-wrap text-muted-foreground">{page.text}</p>
              </section>
            ))}
          </div>
        </TabsContent>
        <TabsContent value="ledger" className="mt-4">
          <div className="rounded-xl border bg-card p-4">
            <p className="mb-3 text-[12px] text-muted-foreground">
              Arena runs use an isolated in-memory ledger so parallel jobs do not race. Seed payments are orders already
              refunded.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {world.payments.map((row) => (
                  <TableRow key={`${row.order_id}-${row.at}`} className={cn(row.source === "seed" && "bg-tag-pink/8")}>
                    <TableCell className="font-mono">{row.order_id}</TableCell>
                    <TableCell className="font-mono">€{row.amount_eur}</TableCell>
                    <TableCell>
                      {row.source === "seed" ? <Tag tone="pink">already refunded</Tag> : row.source}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
