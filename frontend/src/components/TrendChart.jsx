import { useEffect, useState } from "react";
import { getTrend } from "../api.js";

const COLORS = ["#5b8def", "#f2994a", "#9b59b6", "#27ae60", "#e74c3c", "#f1c40f"];

export default function TrendChart({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    getTrend(30).then(setRows).catch(() => setRows([]));
  }, [refreshKey]);

  const dates = [...new Set(rows.map((r) => r.date))].sort();
  const sources = [...new Set(rows.map((r) => r.source))];
  const byDate = Object.fromEntries(dates.map((d) => [d, {}]));
  rows.forEach((r) => { byDate[r.date][r.source] = r.tokens; });
  const dayTotals = dates.map((d) => sources.reduce((sum, s) => sum + (byDate[d][s] || 0), 0));
  const maxTotal = Math.max(1, ...dayTotals);

  const sourceTotals = Object.fromEntries(sources.map((s) => [s, 0]));
  rows.forEach((r) => { sourceTotals[r.source] += r.tokens; });
  const grandTotal = Object.values(sourceTotals).reduce((a, b) => a + b, 0) || 1;

  const barWidth = 8;
  const gap = 4;
  const chartHeight = 120;
  const step = barWidth + gap;
  const chartWidth = dates.length * step;
  const xs = dates.map((_, i) => i * step + barWidth / 2);

  // Per date, the cumulative stacked top edge (y-coordinate) for each source,
  // in the same stacking order as `sources`.
  const stackTops = dates.map((date) => {
    let cum = 0;
    return sources.map((source) => {
      cum += byDate[date][source] || 0;
      return chartHeight - (cum / maxTotal) * chartHeight;
    });
  });

  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4 mb-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Usage trend (last 30 days)</h4>
      <svg
        width={chartWidth}
        height={chartHeight}
        role="group"
        aria-label="Usage trend, last 30 days, stacked by source"
      >
        {sources.map((source, si) => {
          const topLine = xs.map((x, i) => `L ${x},${stackTops[i][si]}`).join(" ");
          const bottomLine = xs
            .slice()
            .reverse()
            .map((x, revIdx) => {
              const i = xs.length - 1 - revIdx;
              const y = si > 0 ? stackTops[i][si - 1] : chartHeight;
              return `L ${x},${y}`;
            })
            .join(" ");
          const d = `M ${xs[0]},${stackTops[0][si]} ${topLine} ${bottomLine} Z`;
          const label = `${source}: ${(sourceTotals[source] || 0).toLocaleString()} tokens`;
          return (
            <path
              key={source}
              d={d}
              fill={COLORS[si % COLORS.length]}
              role="img"
              aria-label={label}
              tabIndex={0}
            >
              <title>{label}</title>
            </path>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-4 mt-2 text-xs">
        {sources.map((s, i) => (
          <span key={s} className="flex items-center gap-1">
            <i className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: COLORS[i % COLORS.length] }} />
            {s}: {((sourceTotals[s] / grandTotal) * 100).toFixed(1)}%
          </span>
        ))}
      </div>
    </div>
  );
}
