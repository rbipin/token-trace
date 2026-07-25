import { useEffect, useState } from "react";
import { getTrend } from "../api.js";
import { harnessColor, useThemeCtx } from "../theme.js";

const W = 400;
const H = 150;
const PAD_B = 4;

// Catmull-Rom-ish smoothing through a series of [x, y] points, clamped so
// control points never overshoot past their neighbors' y-range.
function smooth(pts) {
  if (pts.length < 3) {
    return pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  }
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)} `;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    let c1x = p1[0] + (p2[0] - p0[0]) / 9;
    let c1y = p1[1] + (p2[1] - p0[1]) / 9;
    let c2x = p2[0] - (p3[0] - p1[0]) / 9;
    let c2y = p2[1] - (p3[1] - p1[1]) / 9;
    const lo = Math.min(p1[1], p2[1]);
    const hi = Math.max(p1[1], p2[1]);
    c1y = Math.max(lo, Math.min(hi, c1y));
    c2y = Math.max(lo, Math.min(hi, c2y));
    d += `C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)} `;
  }
  return d.trim();
}

export default function TrendChart({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const { dark, accent } = useThemeCtx();

  useEffect(() => {
    getTrend(30).then(setRows).catch(() => setRows([]));
  }, [refreshKey]);

  const dates = [...new Set(rows.map((r) => r.date))].sort();
  const sources = [...new Set(rows.map((r) => r.source))];
  const byDate = Object.fromEntries(dates.map((d) => [d, {}]));
  rows.forEach((r) => {
    byDate[r.date][r.source] = r.tokens;
  });

  const sourceTotals = Object.fromEntries(sources.map((s) => [s, 0]));
  rows.forEach((r) => {
    sourceTotals[r.source] += r.tokens;
  });
  const grandTotal = Object.values(sourceTotals).reduce((a, b) => a + b, 0) || 1;
  const legend = sources
    .map((s) => ({
      label: s,
      color: harnessColor(s, dark, dark ? "#8b8d94" : "#78716c", accent),
      pct: (sourceTotals[s] / grandTotal) * 100,
    }))
    .sort((a, b) => b.pct - a.pct);

  const n = dates.length;
  const dayTotals = dates.map((d) => sources.reduce((sum, s) => sum + (byDate[d][s] || 0), 0));
  const tMax = Math.max(...dayTotals, 1) * 1.08;
  const X = (i) => (n > 1 ? (i / (n - 1)) * W : W / 2);
  const Y = (v) => H - PAD_B - (v / tMax) * (H - PAD_B);

  const topPts = dayTotals.map((v, i) => [X(i), Y(v)]);
  const basePts = dayTotals.map((_, i) => [X(i), Y(0)]);
  const areaPath =
    n > 0
      ? smooth(topPts) +
        ` L${basePts[basePts.length - 1][0].toFixed(1)},${basePts[basePts.length - 1][1].toFixed(1)} ` +
        smooth(basePts.slice().reverse()) +
        " Z"
      : "";
  const linePath = n > 0 ? smooth(topPts) : "";

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <span className="font-bold text-xs tracking-[0.08em] uppercase">Usage trend</span>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full block mt-3.5">
        {areaPath && <path d={areaPath} fill={accent} fillOpacity={0.45} />}
        {linePath && <path d={linePath} fill="none" stroke={accent} strokeWidth={1.75} />}
      </svg>
      <div className="flex justify-between mt-2 font-mono text-[11px] text-subtext dark:text-subtext-dark">
        <span>{dates[0] || "—"}</span>
        <span>{dates[dates.length - 1] || "—"}</span>
      </div>
      <div className="flex gap-4 flex-wrap mt-2.5">
        {legend.map((l) => (
          <span
            key={l.label}
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
