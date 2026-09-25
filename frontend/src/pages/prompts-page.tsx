import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ResultTag, Tag } from "@/components/ui/tag"
import { createConfig, deleteConfig, resetConfig, updateConfig } from "@/lib/api"
import { useArena } from "@/lib/arena-context"
import { cn } from "cn"

export function PromptsPage() {
  const { configs, config, configId, setConfigId, reload, setError, boardsByConfig } = useArena()
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState("Untitled")

  if (!config) {
    return <p className="text-sm text-muted-foreground">No configs loaded.</p>
  }

  return (
    <PromptEditor
      key={config.id}
      config={config}
      configs={configs}
      configId={configId}
      setConfigId={setConfigId}
      reload={reload}
      setError={setError}
      createOpen={createOpen}
      setCreateOpen={setCreateOpen}
      newName={newName}
      setNewName={setNewName}
      boardsByConfig={boardsByConfig}
    />
  )
}

function PromptEditor({
  config,
  configs,
  configId,
  setConfigId,
  reload,
  setError,
  createOpen,
  setCreateOpen,
  newName,
  setNewName,
  boardsByConfig,
}: {
  config: NonNullable<ReturnType<typeof useArena>["config"]>
  configs: ReturnType<typeof useArena>["configs"]
  configId: string
  setConfigId: (id: string) => void
  reload: () => Promise<void>
  setError: (message: string | null) => void
  createOpen: boolean
  setCreateOpen: (open: boolean) => void
  newName: string
  setNewName: (name: string) => void
  boardsByConfig: ReturnType<typeof useArena>["boardsByConfig"]
}) {
  const [name, setName] = useState(config.name)
  const [limit, setLimit] = useState(String(config.refund_auto_limit ?? 50))
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await updateConfig(configId, { name, refund_auto_limit: Number(limit) })
      setDirty(false)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 gap-4">
      <aside className="flex w-64 shrink-0 flex-col overflow-hidden rounded-xl border bg-card">
        <div className="border-b px-3 py-3">
          <h1 className="text-sm font-medium">Configs</h1>
          <p className="text-[12px] text-muted-foreground">
            Same gold labels on every row. Each row sets the auto-refund limit Resolvd uses.
          </p>
        </div>
        <div className="flex flex-1 flex-col gap-1 overflow-auto p-2">
          {configs.map((row) => {
            const board = boardsByConfig[row.id]
            const gateFail = board && board.ran > 0 && (board.gate_fail ?? board.forbidden_write) > 0
            const ran = board && board.ran > 0
            return (
              <button
                key={row.id}
                type="button"
                onClick={() => setConfigId(row.id)}
                className={cn(
                  "rounded-md border px-2.5 py-2 text-left text-sm",
                  row.id === configId ? "border-ring bg-accent" : "border-transparent hover:bg-muted/60"
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="min-w-0 truncate font-medium">{row.name}</span>
                  {row.id === "cap-50" ? <Tag tone="green">ship</Tag> : null}
                  {row.builtin ? <Tag tone="slate">builtin</Tag> : <Tag tone="violet">custom</Tag>}
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="font-mono text-[11px] text-muted-foreground">{row.id}</span>
                  {ran ? <ResultTag kind={gateFail ? "gate" : "pass"} /> : null}
                </div>
              </button>
            )
          })}
          <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
            New config
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">Refund auto limit</h2>
          <p className="text-[12px] text-muted-foreground">
            {config.builtin
              ? "Built-in limit. Cap 50 is the ship row. Reset puts the seed limit back."
              : "Custom limit. Saved on this desk."}
          </p>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-4">
          <div>
            <Label htmlFor="cfg-name">Name</Label>
            <Input
              id="cfg-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setDirty(true)
              }}
            />
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <Label htmlFor="cfg-limit">REFUND_AUTO_LIMIT</Label>
              <span className="font-mono text-[11px] text-muted-foreground">
                {dirty ? "unsaved" : "saved"} · {config.model}
              </span>
            </div>
            <Input
              id="cfg-limit"
              inputMode="decimal"
              value={limit}
              onChange={(event) => {
                setLimit(event.target.value)
                setDirty(true)
              }}
            />
            <p className="mt-2 text-[12px] text-muted-foreground">
              Resolvd can pay a refund at or under this dollar amount. A larger refund escalates and does not pay. Triage is SuperGrok. Gold labels stay fixed when you change the limit.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={!dirty || saving} onClick={() => void save()}>
              {saving ? "Saving…" : "Save"}
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                void createConfig({ name: `${config.name} copy`, instructions: config.instructions, clone_from: config.id }).then((row) => {
                  void reload().then(() => setConfigId(row.id))
                })
              }
            >
              Duplicate
            </Button>
            {config.builtin ? (
              <Button
                variant="outline"
                onClick={() =>
                  void resetConfig(config.id)
                    .then(() => reload())
                    .catch((err: unknown) => setError(err instanceof Error ? err.message : "Reset failed."))
                }
              >
                Reset to seed
              </Button>
            ) : (
              <Button
                variant="destructive"
                onClick={() =>
                  void deleteConfig(config.id)
                    .then(() => {
                      setConfigId("cap-50")
                      return reload()
                    })
                    .catch((err: unknown) => setError(err instanceof Error ? err.message : "Delete failed."))
                }
              >
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New config</DialogTitle>
            <DialogDescription>
              Creates a config with this name. The auto-refund limit starts at $50. Duplicate copies the selected config instead.
            </DialogDescription>
          </DialogHeader>
          <Label htmlFor="new-name">Name</Label>
          <Input id="new-name" value={newName} onChange={(event) => setNewName(event.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                void createConfig({ name: newName, instructions: "" }).then((row) => {
                  setCreateOpen(false)
                  void reload().then(() => setConfigId(row.id))
                })
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
