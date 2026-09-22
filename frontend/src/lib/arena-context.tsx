/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import {
  fetchBoard,
  fetchJob,
  fetchRuns,
  fetchWorld,
  submitJob,
} from "@/lib/api"
import { emptyBoard } from "@/lib/board"
import { normalizeScore } from "@/lib/result"
import type {
  ArenaJob,
  LiveBoard,
  PromptConfig,
  TicketRun,
  World,
} from "@/lib/types"

const STORAGE_KEY = "refund-arena-config"
const EMPTY_RUNS: Record<string, TicketRun> = {}

function normalizeBoard(board: LiveBoard): LiveBoard {
  return {
    ...board,
    runs: (board.runs ?? []).map((row) => ({
      ...row,
      score: normalizeScore(row.score),
    })),
  }
}

function isActiveStatus(status: ArenaJob["status"]): boolean {
  return status === "queued" || status === "running" || status === "cancelling"
}

function mapRuns(rows: TicketRun[]): Record<string, TicketRun> {
  const map: Record<string, TicketRun> = {}
  for (const row of rows) map[row.ticket.id] = row
  return map
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
  queueJob: (body: {
    sample?: number
    all?: boolean
    ticket_ids?: string[]
    concurrency?: number
  }) => Promise<void>
}

const ArenaContext = createContext<ArenaContextValue | null>(null)

export function ArenaProvider({ children }: { children: ReactNode }) {
  const [world, setWorld] = useState<World | null>(null)
  const [configId, setConfigIdState] = useState(
    () => localStorage.getItem(STORAGE_KEY) || "production"
  )
  const [board, setBoardState] = useState<LiveBoard>(() =>
    emptyBoard(0, "production")
  )
  const [boardsByConfig, setBoardsByConfig] = useState<
    Record<string, LiveBoard>
  >({})
  const [runsByConfig, setRunsByConfig] = useState<
    Record<string, Record<string, TicketRun>>
  >({})
  const [jobByConfig, setJobByConfig] = useState<
    Record<string, ArenaJob | null>
  >({})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const configs = useMemo(() => world?.configs ?? [], [world])
  const config =
    configs.find((row) => row.id === configId) ?? configs[0] ?? null
  const activeConfigId = config?.id ?? configId
  const runsByTicket = runsByConfig[activeConfigId] ?? EMPTY_RUNS
  const job = jobByConfig[activeConfigId] ?? null

  const configIdRef = useRef(activeConfigId)
  const boardsRef = useRef(boardsByConfig)
  const ticketCountRef = useRef(0)
  const jobDoneRef = useRef<Record<string, number>>({})
  configIdRef.current = activeConfigId
  boardsRef.current = boardsByConfig
  ticketCountRef.current = world?.tickets.length ?? 0

  const applyBoard = useCallback((next: LiveBoard) => {
    const normalized = normalizeBoard(next)
    const cid = normalized.config_id
    if (cid) {
      boardsRef.current = { ...boardsRef.current, [cid]: normalized }
      setBoardsByConfig((prev) => ({ ...prev, [cid]: normalized }))
    }
    if (!cid || cid === configIdRef.current) {
      setBoardState(normalized)
    }
  }, [])

  const setConfigId = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id)
    setConfigIdState(id)
    const cached = boardsRef.current[id]
    setBoardState(cached ?? emptyBoard(ticketCountRef.current, id))
  }, [])

  const setRun = useCallback((run: TicketRun) => {
    const cid = run.config_id || configIdRef.current
    setRunsByConfig((prev) => ({
      ...prev,
      [cid]: { ...prev[cid], [run.ticket.id]: run },
    }))
  }, [])

  const setJob = useCallback(
    (next: ArenaJob | null) => {
      if (!next) {
        const cid = configIdRef.current
        setJobByConfig((prev) => ({ ...prev, [cid]: null }))
        return
      }
      setJobByConfig((prev) => ({ ...prev, [next.config_id]: next }))
      if (next.board) applyBoard(next.board)
    },
    [applyBoard]
  )

  const loadRuns = useCallback(async (id: string) => {
    const rows = await fetchRuns(id)
    setRunsByConfig((prev) => ({ ...prev, [id]: mapRuns(rows) }))
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
    const next = Object.fromEntries(entries)
    boardsRef.current = { ...boardsRef.current, ...next }
    setBoardsByConfig((prev) => ({ ...prev, ...next }))
  }, [])

  const reload = useCallback(async () => {
    setError(null)
    const next = await fetchWorld()
    setWorld(next)
    const selected = next.configs?.some((row) => row.id === configId)
      ? configId
      : (next.configs?.[0]?.id ?? "production")
    if (selected !== configId) setConfigId(selected)
    const nextBoard = await fetchBoard(selected)
    applyBoard(nextBoard)
    await Promise.all([loadRuns(selected), loadCompare(next.configs ?? [])])
  }, [applyBoard, configId, loadCompare, loadRuns, setConfigId])

  const refreshRuns = useCallback(async () => {
    const nextBoard = await fetchBoard(activeConfigId)
    applyBoard(nextBoard)
    await Promise.all([loadRuns(activeConfigId), loadCompare(configs)])
  }, [activeConfigId, applyBoard, configs, loadCompare, loadRuns])

  const queueJob = useCallback(
    async (body: {
      sample?: number
      all?: boolean
      ticket_ids?: string[]
      concurrency?: number
    }) => {
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
    [activeConfigId, setJob]
  )

  useEffect(() => {
    let cancelled = false
    fetchWorld()
      .then(async (next) => {
        if (cancelled) return
        setWorld(next)
        const selected = next.configs?.some((row) => row.id === configId)
          ? configId
          : (next.configs?.[0]?.id ?? "production")
        if (selected !== configId) setConfigId(selected)
        const nextBoard = await fetchBoard(selected)
        if (cancelled) return
        applyBoard(nextBoard)
        setError(null)
        await Promise.all([loadRuns(selected), loadCompare(next.configs ?? [])])
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(
            err instanceof Error ? err.message : "Backend is not reachable."
          )
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
        applyBoard(nextBoard)
        setRunsByConfig((prev) => ({
          ...prev,
          [activeConfigId]: mapRuns(rows),
        }))
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Could not load board.")
      })
    return () => {
      cancelled = true
    }
  }, [activeConfigId, applyBoard, world])

  const activeJobKey = Object.values(jobByConfig)
    .filter((row): row is ArenaJob =>
      Boolean(row && isActiveStatus(row.status))
    )
    .map((row) => row.id)
    .sort()
    .join(",")

  useEffect(() => {
    if (!activeJobKey) return undefined
    const ids = activeJobKey.split(",")
    const timer = window.setInterval(() => {
      for (const id of ids) {
        void fetchJob(id)
          .then(async (next) => {
            const prevDone = jobDoneRef.current[next.id]
            const advanced =
              next.done > 0 && (prevDone == null || next.done > prevDone)
            jobDoneRef.current[next.id] = next.done
            if (advanced || !isActiveStatus(next.status)) {
              await loadRuns(next.config_id)
            }
            setJobByConfig((prev) => ({ ...prev, [next.config_id]: next }))
            if (next.board) applyBoard(next.board)
            if (!isActiveStatus(next.status)) {
              void loadCompare(configs)
            }
          })
          .catch((err: unknown) => {
            setError(err instanceof Error ? err.message : "Job poll failed.")
          })
      }
    }, 800)
    return () => window.clearInterval(timer)
  }, [activeJobKey, applyBoard, configs, loadCompare, loadRuns])

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
      setBoard: applyBoard,
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
      applyBoard,
      setJob,
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
