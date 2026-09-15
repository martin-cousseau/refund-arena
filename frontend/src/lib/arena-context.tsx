/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { fetchBoard, fetchJob, fetchRuns, fetchWorld, submitJob } from "@/lib/api"
import { emptyBoard } from "@/lib/board"
import { normalizeScore } from "@/lib/result"
import type { ArenaJob, LiveBoard, PromptConfig, TicketRun, World } from "@/lib/types"

const STORAGE_KEY = "refund-arena-config"

function normalizeBoard(board: LiveBoard): LiveBoard {
  return {
    ...board,
    runs: (board.runs ?? []).map((row) => ({ ...row, score: normalizeScore(row.score) })),
  }
}

function isActiveStatus(status: ArenaJob["status"]): boolean {
  return status === "queued" || status === "running" || status === "cancelling"
}

type ArenaContextValue = {
  world: World | null
  configs: PromptConfig[]
  configId: string
  config: PromptConfig | null
  board: LiveBoard
  boardsByConfig: Record<string, LiveBoard>
  runsByTicket: Record<string, TicketRun>
  job: ArenaJob | null
  error: string | null
  loading: boolean
  setConfigId: (id: string) => void
  setError: (message: string | null) => void
  setBoard: (board: LiveBoard) => void
  setJob: (job: ArenaJob | null) => void
  setRun: (run: TicketRun) => void
  reload: () => Promise<void>
  refreshRuns: () => Promise<void>
  queueJob: (body: { sample?: number; all?: boolean; ticket_ids?: string[]; concurrency?: number }) => Promise<void>
}

const ArenaContext = createContext<ArenaContextValue | null>(null)

export function ArenaProvider({ children }: { children: ReactNode }) {
  const [world, setWorld] = useState<World | null>(null)
  const [configId, setConfigIdState] = useState(() => localStorage.getItem(STORAGE_KEY) || "production")
  const [board, setBoardState] = useState<LiveBoard>(() => emptyBoard(0, "production"))
  const [boardsByConfig, setBoardsByConfig] = useState<Record<string, LiveBoard>>({})
  const [runsByTicket, setRunsByTicket] = useState<Record<string, TicketRun>>({})
  const [job, setJob] = useState<ArenaJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const configs = useMemo(() => world?.configs ?? [], [world])
  const config = configs.find((row) => row.id === configId) ?? configs[0] ?? null
  const activeConfigId = config?.id ?? configId

  const setConfigId = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id)
    setConfigIdState(id)
  }, [])

  const setBoard = useCallback((next: LiveBoard) => {
    const normalized = normalizeBoard(next)
    setBoardState(normalized)
    if (normalized.config_id) {
      setBoardsByConfig((prev) => ({ ...prev, [normalized.config_id!]: normalized }))
    }
  }, [])

  const setRun = useCallback((run: TicketRun) => {
    setRunsByTicket((prev) => ({ ...prev, [run.ticket.id]: run }))
  }, [])

  const loadRuns = useCallback(async (id: string) => {
    const rows = await fetchRuns(id)
    const map: Record<string, TicketRun> = {}
    for (const row of rows) map[row.ticket.id] = row
    setRunsByTicket(map)
  }, [])

  const loadCompare = useCallback(async (rows: PromptConfig[]) => {
    const entries = await Promise.all(
      rows.map(async (row) => {
        try {
          return [row.id, await fetchBoard(row.id)] as const
        } catch {
          return [row.id, emptyBoard(0, row.id)] as const
        }
      })
    )
    setBoardsByConfig(Object.fromEntries(entries))
  }, [])

  const reload = useCallback(async () => {
    setError(null)
    const next = await fetchWorld()
    setWorld(next)
    const selected = next.configs?.some((row) => row.id === configId)
      ? configId
      : next.configs?.[0]?.id ?? "production"
    if (selected !== configId) setConfigId(selected)
    const nextBoard = await fetchBoard(selected)
    setBoard(nextBoard)
    await Promise.all([loadRuns(selected), loadCompare(next.configs ?? [])])
  }, [configId, loadCompare, loadRuns, setBoard, setConfigId])

  const refreshRuns = useCallback(async () => {
    const nextBoard = await fetchBoard(activeConfigId)
    setBoard(nextBoard)
    await Promise.all([loadRuns(activeConfigId), loadCompare(configs)])
  }, [activeConfigId, configs, loadCompare, loadRuns, setBoard])

  const queueJob = useCallback(
    async (body: { sample?: number; all?: boolean; ticket_ids?: string[]; concurrency?: number }) => {
      setError(null)
      const next = await submitJob({
        config_id: activeConfigId,
        concurrency: body.concurrency ?? 4,
        sample: body.sample,
        all: body.all,
        ticket_ids: body.ticket_ids,
      })
      setJob(next)
    },
    [activeConfigId]
  )

  useEffect(() => {
    let cancelled = false
    fetchWorld()
      .then(async (next) => {
        if (cancelled) return
        setWorld(next)
        const selected = next.configs?.some((row) => row.id === configId)
          ? configId
          : next.configs?.[0]?.id ?? "production"
        if (selected !== configId) setConfigId(selected)
        const nextBoard = await fetchBoard(selected)
        if (cancelled) return
        setBoard(nextBoard)
        setError(null)
        await Promise.all([loadRuns(selected), loadCompare(next.configs ?? [])])
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Backend is not reachable.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // boot once; config switches refetch below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!world) return
    let cancelled = false
    Promise.all([fetchBoard(activeConfigId), fetchRuns(activeConfigId)])
      .then(([nextBoard, rows]) => {
        if (cancelled) return
        setBoard(nextBoard)
        const map: Record<string, TicketRun> = {}
        for (const row of rows) map[row.ticket.id] = row
        setRunsByTicket(map)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load board.")
      })
    return () => {
      cancelled = true
    }
  }, [activeConfigId, setBoard, world])

  useEffect(() => {
    if (!job || !isActiveStatus(job.status)) return undefined
    const timer = window.setInterval(() => {
      void fetchJob(job.id)
        .then((next) => {
          setJob(next)
          if (next.board) setBoard(next.board)
          if (!isActiveStatus(next.status)) {
            void loadRuns(activeConfigId)
            void loadCompare(configs)
          }
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err.message : "Job poll failed.")
        })
    }, 800)
    return () => window.clearInterval(timer)
  }, [activeConfigId, configs, job, loadCompare, loadRuns, setBoard])

  const value = useMemo(
    () => ({
      world,
      configs,
      configId: activeConfigId,
      config,
      board,
      boardsByConfig,
      runsByTicket,
      job,
      error,
      loading,
      setConfigId,
      setError,
      setBoard,
      setJob,
      setRun,
      reload,
      refreshRuns,
      queueJob,
    }),
    [
      world,
      configs,
      activeConfigId,
      config,
      board,
      boardsByConfig,
      runsByTicket,
      job,
      error,
      loading,
      setConfigId,
      setBoard,
      setRun,
      reload,
      refreshRuns,
      queueJob,
    ]
  )

  return <ArenaContext.Provider value={value}>{children}</ArenaContext.Provider>
}

export function useArena() {
  const ctx = useContext(ArenaContext)
  if (!ctx) {
    throw new Error("useArena must be used within ArenaProvider")
  }
  return ctx
}
