import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { useNavigate } from "react-router-dom"

type ClauseRow = { clause: string; ran: number; pass: number; pct: number }

function ClauseTip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: ClauseRow }[]
}) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  return (
    <div className="rounded-lg border bg-card px-2 py-1.5 text-[12px] shadow-sm">
      <div className="font-medium">{row.clause}</div>
      <div className="text-muted-foreground">
        {row.ran ? `${row.pass}/${row.ran} desk pass · ${row.pct}%` : "not run"}
      </div>
    </div>
  )
}

export function ClauseBars({ data }: { data: ClauseRow[] }) {
  const navigate = useNavigate()
  const chartData = data.map((row) => ({
    ...row,
    pct: row.ran ? row.pct : 0,
    rest: row.ran ? Math.max(0, 100 - row.pct) : 0,
  }))

  return (
    <div className="h-[220px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          barCategoryGap={6}
          onClick={(state) => {
            const clause = state?.activeLabel
            if (typeof clause === "string") navigate(`/queue?clause=${encodeURIComponent(clause)}`)
          }}
        >
          <XAxis dataKey="clause" tick={{ fontSize: 10 }} interval={0} tickLine={false} axisLine={false} />
          <YAxis
            domain={[0, 100]}
            width={28}
            tick={{ fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ClauseTip />} cursor={{ fill: "var(--muted)" }} />
          <Bar dataKey="pct" stackId="rate" fill="#17C37B" cursor="pointer" isAnimationActive={false} />
          <Bar
            dataKey="rest"
            stackId="rate"
            fill="var(--muted)"
            radius={[3, 3, 0, 0]}
            cursor="pointer"
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
