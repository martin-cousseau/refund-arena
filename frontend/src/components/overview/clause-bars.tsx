import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { useNavigate } from "react-router-dom"

export function ClauseBars({
  data,
}: {
  data: { clause: string; ran: number; pass: number; pct: number }[]
}) {
  const navigate = useNavigate()
  const chartData = data.map((row) => ({ ...row, fail: Math.max(0, 100 - row.pct) }))

  return (
    <div className="h-[220px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 4, left: -18, bottom: 0 }}
          barCategoryGap={8}
          onClick={(state) => {
            const clause = state?.activeLabel
            if (typeof clause === "string") navigate(`/queue?clause=${encodeURIComponent(clause)}`)
          }}
        >
          <XAxis dataKey="clause" tick={{ fontSize: 10 }} interval={0} tickLine={false} axisLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip
            formatter={(value, name) => [
              `${String(value)}${name === "pct" ? "%" : ""}`,
              name === "pct" ? "pass" : String(name),
            ]}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--card)",
              fontSize: 12,
            }}
          />
          <Bar dataKey="pct" fill="#17c37b" radius={[3, 3, 0, 0]} cursor="pointer" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
