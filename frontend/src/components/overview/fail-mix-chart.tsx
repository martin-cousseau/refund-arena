import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { useNavigate } from "react-router-dom"

import type { MixSlice } from "@/lib/stats"

export function FailMixChart({ data }: { data: MixSlice[] }) {
  const navigate = useNavigate()
  const total = data.reduce((sum, row) => sum + row.count, 0)

  if (total === 0) {
    return (
      <div className="flex h-[220px] flex-col items-center justify-center gap-1 text-center">
        <p className="text-sm font-medium text-tag-green">Desk is clean</p>
        <p className="text-[12px] text-muted-foreground">No primary fails on this board.</p>
      </div>
    )
  }

  return (
    <div className="grid h-[220px] grid-cols-[minmax(0,1fr)_minmax(0,140px)] items-center gap-2">
      <div className="h-full min-h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="label"
            innerRadius={48}
            outerRadius={78}
            paddingAngle={2}
            stroke="transparent"
            isAnimationActive={false}
            onClick={(entry) => {
              const rec = entry as { key?: string; payload?: MixSlice }
              const key = rec.payload?.key ?? rec.key
              if (key) navigate(`/runs?fail=${encodeURIComponent(key)}`)
            }}
          >
            {data.map((row) => (
              <Cell key={row.key} fill={row.color} className="cursor-pointer outline-none" />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [`${String(value)}`, String(name)]}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--card)",
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      </div>
      <ul className="flex flex-col gap-1.5">
        {data.map((row) => (
          <li key={row.key}>
            <button
              type="button"
              className="flex w-full items-center gap-2 text-left text-[11px]"
              onClick={() => navigate(`/runs?fail=${encodeURIComponent(row.key)}`)}
            >
              <span className="size-2 shrink-0 rounded-sm" style={{ background: row.color }} />
              <span className="min-w-0 truncate">{row.label}</span>
              <span className="ml-auto font-mono tabular-nums">{row.count}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
