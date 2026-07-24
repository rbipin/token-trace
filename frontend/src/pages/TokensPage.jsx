import { useEffect, useState } from "react";
import { getSummary } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsRow from "../components/StatsRow.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRefreshKey((k) => k + 1);
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range]);

  return (
    <div>
      <RangeTabs value={range} onChange={setRange} />
      <div className="grid-2">
        <StatsRow summary={summary} />
        <SyncLogCard refreshKey={refreshKey} />
      </div>
      <Heatmap refreshKey={refreshKey} />
      <TrendChart refreshKey={refreshKey} />
      <div className="card">
        <h3>{summary ? summary.total_tokens.toLocaleString() : "—"} tokens</h3>
        <HarnessCards summary={summary} />
      </div>
      <ContextBreakdown summary={summary} />
    </div>
  );
}
