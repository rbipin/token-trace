import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getTrend } from "../api.js";
import { formatTokens } from "../format.js";
import { harnessColor, harnessLabel, useThemeCtx } from "../theme.js";

function TrendTooltip({ active, payload, label, subtext }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-lg border border-border dark:border-border-dark bg-card dark:bg-card-dark px-3 py-2 text-xs shadow-lg"
      style={{ minWidth: 140 }}
    >
      <div className="font-mono font-semibold mb-1">{label}</div>
      {payload
        .filter((p) => p.value)
        .map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5" style={{ color: subtext }}>
              <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: p.color }} />
              {harnessLabel(p.dataKey)}
            </span>
            <span className="font-mono font-semibold">{formatTokens(p.value).abbreviated}</span>
          </div>
        ))}
    </div>
  );
}

export default function TrendChart({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const { dark, accent } = useThemeCtx();
  const subtext = dark ? "#8b8d94" : "#78716c";

  useEffect(() => {
    getTrend(30).then(setRows).catch(() => setRows([]));
  }, [refreshKey]);

  const dates = [...new Set(rows.map((r) => r.date))].sort();
  const sources = [...new Set(rows.map((r) => r.source))];
  const byDate = Object.fromEntries(dates.map((d) => [d, { date: d }]));
  rows.forEach((r) => {
    byDate[r.date][r.source] = r.tokens;
  });
  const chartData = dates.map((d) => byDate[d]);

  const sourceTotals = Object.fromEntries(sources.map((s) => [s, 0]));
  rows.forEach((r) => {
    sourceTotals[r.source] += r.tokens;
  });
  const grandTotal = Object.values(sourceTotals).reduce((a, b) => a + b, 0) || 1;
  const legend = sources
    .map((s) => ({
      source: s,
      label: harnessLabel(s),
      color: harnessColor(s, dark, subtext, accent),
      pct: (sourceTotals[s] / grandTotal) * 100,
    }))
    .sort((a, b) => b.pct - a.pct);

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <span className="font-bold text-xs tracking-[0.08em] uppercase">Usage trend</span>
      <div className="mt-3.5" style={{ height: 150 }}>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
              <defs>
                {legend.map((l) => (
                  <linearGradient key={l.source} id={`trend-${l.source}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={l.color} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={l.color} stopOpacity={0.03} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={subtext} strokeOpacity={0.15} vertical={false} />
              <XAxis dataKey="date" hide />
              <YAxis
                width={36}
                tickFormatter={(v) => formatTokens(v).abbreviated}
                tick={{ fontSize: 10, fill: subtext }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<TrendTooltip subtext={subtext} />} />
              {sources.map((s) => (
                <Area
                  key={s}
                  type="monotone"
                  dataKey={s}
                  stackId="tokens"
                  stroke={harnessColor(s, dark, subtext, accent)}
                  strokeWidth={1.75}
                  fill={`url(#trend-${s})`}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-[11px] text-subtext dark:text-subtext-dark">
            No data.
          </div>
        )}
      </div>
      <div className="flex justify-between mt-2 font-mono text-[11px] text-subtext dark:text-subtext-dark">
        <span>{dates[0] || "—"}</span>
        <span>{dates[dates.length - 1] || "—"}</span>
      </div>
      <div className="flex gap-4 flex-wrap mt-2.5">
        {legend.map((l) => (
          <span
            key={l.source}
            className="flex items-center gap-1.5 text-[11px] font-medium text-subtext dark:text-subtext-dark"
          >
            <span className="w-[9px] h-[9px] rounded-sm" style={{ background: l.color }} />
            {l.label} {l.pct.toFixed(1)}%
          </span>
        ))}
        {legend.length === 0 && <span className="text-[11px] text-subtext dark:text-subtext-dark">No data.</span>}
      </div>
    </div>
  );
}
