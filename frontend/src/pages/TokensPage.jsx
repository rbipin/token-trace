import { useEffect, useState } from "react";
import { getSummary, getMeta } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsRow from "../components/StatsRow.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import ModelBreakdown from "../components/ModelBreakdown.jsx";
import { formatTokens } from "../format.js";
import { formatRelativeTime } from "../relativeTime.js";
import { harnessColor, useThemeCtx } from "../theme.js";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [mostRecent, setMostRecent] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { dark, accent } = useThemeCtx();

  useEffect(() => {
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range, refreshKey]);

  useEffect(() => {
    getMeta().then((data) => setMostRecent(data.most_recent_data_at)).catch(() => {});
  }, [refreshKey]);

  const tokens = summary ? formatTokens(summary.total_tokens) : null;
  const progressSegs = summary
    ? summary.harnesses.map((h) => ({
        source: h.source,
        pct: h.pct * 100,
        color: harnessColor(h.source, dark, dark ? "#8b8d94" : "#78716c", accent),
      }))
    : [];

  return (
    <div>
      <div className="flex justify-end mb-3.5">
        <span className="inline-flex items-center gap-2 text-xs font-medium text-subtext dark:text-subtext-dark">
          <span className="w-[7px] h-[7px] rounded-full" style={{ background: accent }} />
          Most recent data: {mostRecent ? formatRelativeTime(mostRecent) : "—"}
        </span>
      </div>

      <div className="grid gap-5 items-start" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
        <div className="flex flex-col gap-5">
          <StatsRow summary={summary} />
          <Heatmap refreshKey={refreshKey} />
          <TrendChart refreshKey={refreshKey} />
          <SyncLogCard refreshKey={refreshKey} />
        </div>

        <div className="flex flex-col gap-5">
          <div className="border border-border dark:border-border-dark rounded-[14px] px-[26px] pt-[22px] pb-[26px] bg-card dark:bg-card-dark">
            <div className="flex items-center justify-between flex-wrap gap-2.5 mb-[22px]">
              <RangeTabs value={range} onChange={setRange} />
              <div className="flex gap-2 shrink-0">
                <button className="tt-tab flex items-center gap-1.5 px-3.5 py-2 border border-border dark:border-border-dark rounded-[9px] text-xs font-semibold whitespace-nowrap">
                  ↗ Share
                </button>
                <button
                  className="tt-tab px-3 py-2 border border-border dark:border-border-dark rounded-[9px]"
                  onClick={() => setRefreshKey((k) => k + 1)}
                  aria-label="Refresh"
                >
                  ⟳
                </button>
              </div>
            </div>
            <div className="text-[11px] font-semibold tracking-[0.14em] uppercase text-subtext dark:text-subtext-dark">
              Total tokens
            </div>
            <div className="flex items-baseline gap-3.5 flex-wrap mt-1.5">
              <span className="font-extrabold text-[clamp(38px,5vw,58px)] leading-[1.05] tracking-[-0.02em]">
                {tokens ? tokens.full : "—"}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-pill dark:bg-pill-dark mt-5 overflow-hidden flex">
              {progressSegs.map((s) => (
                <div key={s.source} style={{ width: `${s.pct}%`, background: s.color }} />
              ))}
            </div>
            <HarnessCards summary={summary} />
          </div>
          <ContextBreakdown summary={summary} />
          <ModelBreakdown summary={summary} />
        </div>
      </div>
    </div>
  );
}
