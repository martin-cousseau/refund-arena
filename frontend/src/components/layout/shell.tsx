import { HugeiconsIcon } from "@hugeicons/react"
import {
  Analytics01Icon,
  LayoutDashboardIcon,
  Menu01Icon,
  Moon02Icon,
  RefreshIcon,
  Search01Icon,
  SourceCodeIcon,
  Store01Icon,
  Sun03Icon,
  Ticket01Icon,
} from "@hugeicons/core-free-icons"
import { NavLink, Outlet } from "react-router-dom"
import { useState } from "react"

import { CommandPalette } from "@/components/layout/command-palette"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { useTheme } from "@/components/theme-provider"
import { useArena } from "@/lib/arena-context"
import { failCount } from "@/lib/stats"
import { cn } from "cn"

const NAV = [
  { to: "/", label: "Overview", hint: "Gate & graphs", icon: LayoutDashboardIcon, end: true },
  { to: "/queue", label: "Queue", hint: "Review tickets", icon: Ticket01Icon, badge: true },
  { to: "/runs", label: "Runs", hint: "Latest per ticket", icon: Analytics01Icon },
  { to: "/shop", label: "Shop", hint: "Orders & policy", icon: Store01Icon },
  { to: "/prompts", label: "Prompts", hint: "Configs", icon: SourceCodeIcon },
]

function SideNav({ onNavigate, fails }: { onNavigate?: () => void; fails: number }) {
  return (
    <>
      <div className="border-b px-4 py-4">
        <p className="text-base font-medium tracking-tight">
          Refund <span className="text-tag-green">Arena</span>
        </p>
        <p className="mt-1 text-[11px] leading-snug text-muted-foreground">North & Co · the write is the score</p>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-2">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                isActive ? "bg-sidebar-accent text-foreground" : "text-muted-foreground hover:bg-sidebar-accent/70"
              )
            }
          >
            <HugeiconsIcon icon={item.icon} strokeWidth={1.8} className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">
              <span className="block font-medium">{item.label}</span>
              <span className="block text-[11px] text-muted-foreground">{item.hint}</span>
            </span>
            {item.badge && fails > 0 ? (
              <span className="rounded bg-tag-rose px-1.5 py-0.5 font-mono text-[10px] text-white tabular-nums">
                {fails}
              </span>
            ) : null}
          </NavLink>
        ))}
      </nav>
      <div className="border-t px-4 py-3 text-[11px] leading-relaxed text-muted-foreground">
        Eval plate for a helpdesk that pays. Ship iff forbidden-write is 0 on Production.
      </div>
    </>
  )
}

export function Shell() {
  const { configs, configId, setConfigId, board, error, setError, reload, world } = useArena()
  const { theme, setTheme } = useTheme()
  const [menu, setMenu] = useState(false)
  const fails = failCount(board)
  const gateFail = board.forbidden_write === 1
  const resolvedDark =
    theme === "dark" || (theme === "system" && typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches)

  return (
    <div className="flex h-svh bg-background">
      <aside className="hidden w-[220px] shrink-0 flex-col border-r bg-sidebar md:flex">
        <SideNav fails={fails} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
          <Button size="icon-sm" variant="ghost" className="md:hidden" onClick={() => setMenu(true)}>
            <HugeiconsIcon icon={Menu01Icon} strokeWidth={2} />
            <span className="sr-only">Menu</span>
          </Button>
          <label className="hidden text-[11px] text-muted-foreground sm:block">Config</label>
          <select
            className="h-8 max-w-[160px] rounded-md border border-input bg-background px-2 text-sm"
            value={configId}
            onChange={(event) => setConfigId(event.target.value)}
          >
            {configs.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
                {row.builtin ? "" : " · custom"}
              </option>
            ))}
          </select>
          <div className="ml-auto flex min-w-0 items-center gap-2 font-mono text-[11px] tabular-nums sm:gap-3">
            <span className="hidden text-muted-foreground sm:inline">
              {board.ran}/{board.total}
            </span>
            <span
              className={cn(
                "shrink-0 rounded px-1.5 py-0.5 font-medium",
                gateFail ? "bg-tag-rose text-white pulse-fail" : "bg-tag-green/15 text-tag-green"
              )}
            >
              GATE {board.forbidden_write}
            </span>
            <span className="hidden text-muted-foreground sm:inline">miss {board.missed_refund}</span>
            <Button
              size="icon-xs"
              variant="ghost"
              onClick={() => {
                const next = document.documentElement.classList.contains("dark") ? "light" : "dark"
                setTheme(next)
              }}
              title="Toggle theme (D)"
            >
              <HugeiconsIcon icon={resolvedDark ? Sun03Icon : Moon02Icon} strokeWidth={2} className="size-3.5" />
            </Button>
            <Button size="icon-xs" variant="ghost" onClick={() => void reload()} title="Reload">
              <HugeiconsIcon icon={RefreshIcon} strokeWidth={2} className="size-3.5" />
            </Button>
            <Button size="xs" variant="outline" className="hidden gap-1 sm:inline-flex" onClick={() => {
              window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))
            }}>
              <HugeiconsIcon icon={Search01Icon} strokeWidth={2} className="size-3" />
              ⌘K
            </Button>
          </div>
        </header>

        {world && world.xai_signed_in === false ? (
          <div className="border-b px-4 py-2">
            <Alert>
              <AlertTitle>SuperGrok</AlertTitle>
              <AlertDescription>
                Sign in once, then reload:{" "}
                <code className="font-mono text-xs">docker compose exec backend python -m app.xai_login</code>
              </AlertDescription>
            </Alert>
          </div>
        ) : null}

        {error ? (
          <div className="border-b px-4 py-2">
            <Alert variant="destructive">
              <AlertTitle>Backend</AlertTitle>
              <AlertDescription className="flex items-center justify-between gap-3">
                <span>{error}</span>
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => {
                    setError(null)
                    void reload()
                  }}
                >
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          </div>
        ) : null}

        <main className="min-h-0 flex-1 overflow-hidden p-4">
          <Outlet />
        </main>
      </div>

      <CommandPalette />

      <Sheet open={menu} onOpenChange={setMenu}>
        <SheetContent side="left" className="w-[220px] bg-sidebar p-0 sm:max-w-[220px]">
          <SideNav fails={fails} onNavigate={() => setMenu(false)} />
        </SheetContent>
      </Sheet>
    </div>
  )
}
