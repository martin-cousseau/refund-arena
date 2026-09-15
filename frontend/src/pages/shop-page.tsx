import { useNavigate } from "react-router-dom"

import { OrderCard } from "@/components/desk/order-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tag } from "@/components/ui/tag"
import { useArena } from "@/lib/arena-context"
import { cn } from "cn"

function PolicyDoc({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/)
  return (
    <div className="flex flex-col gap-4">
      {blocks.map((block, index) => {
        const lines = block.split("\n").filter((line) => !/^=+$/.test(line.trim()))
        if (lines.length === 0) return null
        const heading = lines[0] && lines[0].length < 40 && !lines[0].startsWith("-") && lines.length > 1
        if (heading) {
          return (
            <section key={index}>
              <h3 className="mb-1.5 text-sm font-medium tracking-tight">{lines[0]}</h3>
              <p className="text-[13px] leading-relaxed whitespace-pre-wrap text-muted-foreground">{lines.slice(1).join("\n")}</p>
            </section>
          )
        }
        return (
          <p key={index} className="text-[13px] leading-relaxed whitespace-pre-wrap">
            {block}
          </p>
        )
      })}
    </div>
  )
}

export function ShopPage() {
  const { world, loading } = useArena()
  const navigate = useNavigate()
  if (loading || !world) {
    return <Skeleton className="h-[60vh]" />
  }
  const traps = new Set(world.trap_order_ids)

  return (
    <div className="mx-auto h-full max-w-5xl overflow-auto">
      <div className="mb-4">
        <h1 className="text-lg font-medium tracking-tight">North & Co</h1>
        <p className="text-[13px] text-muted-foreground">
          Eight orders. One policy. The agent must read both through tools. Window {world.refund_window_days}d · cap €
          {world.amount_cap_eur}.
        </p>
      </div>
      <Tabs defaultValue="orders">
        <TabsList>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="policy">Policy</TabsTrigger>
          <TabsTrigger value="ledger">Seed ledger</TabsTrigger>
        </TabsList>
        <TabsContent value="orders" className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {world.orders.map((row) => (
              <OrderCard
                key={row.id}
                order={row}
                trapIds={traps}
                windowDays={world.refund_window_days}
                cap={world.amount_cap_eur}
                onClick={() => navigate(`/queue?order=${row.id}`)}
              />
            ))}
          </div>
        </TabsContent>
        <TabsContent value="policy" className="mt-4">
          <div className="rounded-xl border bg-card p-5">
            <p className="mb-4 text-[12px] text-muted-foreground">
              The Policy config inlines this. Production still calls read_policy.
            </p>
            <PolicyDoc text={world.policy} />
          </div>
        </TabsContent>
        <TabsContent value="ledger" className="mt-4">
          <div className="rounded-xl border bg-card p-4">
            <p className="mb-3 text-[12px] text-muted-foreground">
              Arena runs use an isolated in-memory ledger so parallel jobs do not race. 1114 is already refunded in the seed.
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
                  <TableRow key={`${row.order_id}-${row.at}`} className={cn(row.order_id === "1114" && "bg-tag-pink/8")}>
                    <TableCell className="font-mono">{row.order_id}</TableCell>
                    <TableCell className="font-mono">€{row.amount_eur}</TableCell>
                    <TableCell>
                      {row.order_id === "1114" ? <Tag tone="pink">already refunded</Tag> : row.source}
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
