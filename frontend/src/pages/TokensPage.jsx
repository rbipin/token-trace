import { useEffect, useState } from "react";
import { getSummary, getMeta } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsRow from "../components/StatsRow.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import { formatTokens } from "../format.js";
import { formatRelativeTime } from "../relativeTime.js";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [mostRecent, setMostRecent] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRefreshKey((k) => k + 1);
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range]);

  useEffect(() => {
    getMeta().then((data) => setMostRecent(data.most_recent_data_at)).catch(() => {});
  }, [refreshKey]);

  const tokens = summary ? formatTokens(summary.total_tokens) : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <RangeTabs value={range} onChange={setRange} />
        <span className="text-xs opacity-60">
          Most recent data: {mostRecent ? formatRelativeTime(mostRecent) : "—"}
        </span>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <StatsRow summary={summary} />
        <SyncLogCard refreshKey={refreshKey} />
      </div>
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-6 mb-4">
        <h2 className="text-4xl font-semibold mb-1">{tokens ? tokens.full : "—"}</h2>
        <p className="text-xs uppercase tracking-wide opacity-60 mb-4">Total tokens</p>
        <ContextBreakdown summary={summary} />
        <HarnessCards summary={summary} />
      </div>
      <Heatmap refreshKey={refreshKey} />
      <TrendChart refreshKey={refreshKey} />
    </div>
  );
}
