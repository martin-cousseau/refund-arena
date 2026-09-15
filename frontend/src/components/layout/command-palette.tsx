import { useEffect, useMemo, useState, type ReactNode } from "react"
import { useNavigate } from "react-router-dom"

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useArena } from "@/lib/arena-context"
import { cn } from "cn"

const PAGES = [
  { to: "/", label: "Overview", hint: "Dashboard" },
  { to: "/queue", label: "Queue", hint: "Tickets" },
  { to: "/runs", label: "Runs", hint: "Table" },
  { to: "/shop", label: "Shop", hint: "World" },
  { to: "/prompts", label: "Prompts", hint: "Configs" },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const navigate = useNavigate()
  const { world, setConfigId, configs } = useArena()

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setOpen((value) => !value)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const q = query.trim().toLowerCase()
  const tickets = useMemo(() => {
    const rows = world?.tickets ?? []
    if (!q) return rows.slice(0, 8)
    return rows
      .filter((row) => `${row.id} ${row.title} ${row.clause}`.toLowerCase().includes(q))
      .slice(0, 12)
  }, [q, world])

  const pages = PAGES.filter((row) => !q || `${row.label} ${row.hint}`.toLowerCase().includes(q))
  const matchedConfigs = configs.filter((row) => !q || `${row.name} ${row.id}`.toLowerCase().includes(q))

  function go(path: string) {
    setOpen(false)
    setQuery("")
    navigate(path)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setQuery("")
      }}
    >
      <DialogContent className="max-w-lg p-0">
        <DialogTitle className="sr-only">Jump to</DialogTitle>
        <Input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Jump to a page, ticket, or config"
          className="h-11 rounded-none rounded-t-xl border-0 border-b"
        />
        <div className="max-h-80 overflow-auto p-1">
          {pages.length > 0 ? (
            <Group label="Pages">
              {pages.map((row) => (
                <Item key={row.to} onClick={() => go(row.to)} title={row.label} hint={row.hint} />
              ))}
            </Group>
          ) : null}
          {matchedConfigs.length > 0 ? (
            <Group label="Configs">
              {matchedConfigs.map((row) => (
                <Item
                  key={row.id}
                  onClick={() => {
                    setConfigId(row.id)
                    setOpen(false)
                    setQuery("")
                  }}
                  title={row.name}
                  hint={row.id}
                />
              ))}
            </Group>
          ) : null}
          {tickets.length > 0 ? (
            <Group label="Tickets">
              {tickets.map((row) => (
                <Item
                  key={row.id}
                  onClick={() => go(`/queue/${row.id}`)}
                  title={row.title}
                  hint={row.id}
                  mono
                />
              ))}
            </Group>
          ) : null}
          {pages.length + matchedConfigs.length + tickets.length === 0 ? (
            <p className="px-3 py-6 text-sm text-muted-foreground">Nothing matches.</p>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="py-1">
      <p className="px-2 py-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
      {children}
    </div>
  )
}

function Item({
  title,
  hint,
  onClick,
  mono,
}: {
  title: string
  hint: string
  onClick: () => void
  mono?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted"
    >
      <span className="truncate">{title}</span>
      <span className={cn("text-[11px] text-muted-foreground", mono && "font-mono")}>{hint}</span>
    </button>
  )
}
