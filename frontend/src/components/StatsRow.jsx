import { formatTokens } from "../format.js";

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs opacity-60">{label}</div>
    </div>
  );
}

export default function StatsRow({ summary }) {
  if (!summary) {
    return (
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
        Loading…
      </div>
    );
  }
  const rolling = summary.rolling;
  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-4">
        <Stat label="Last 7d" value={formatTokens(rolling["7d"].total_tokens).abbreviated} />
        <Stat label="Last 30d" value={formatTokens(rolling["30d"].total_tokens).abbreviated} />
        <Stat label="Avg/active day" value={formatTokens(Math.round(rolling.avg_per_active_day)).abbreviated} />
        <Stat label="This month" value={formatTokens(rolling.month.total_tokens).abbreviated} />
        <Stat label="Started" value={summary.first_date || "—"} />
        <Stat label="Active days" value={summary.active_days} />
      </div>
      <div>
        <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Top models</h4>
        <ol className="space-y-1 text-sm">
          {summary.models.slice(0, 5).map((m) => (
            <li key={m.model} className="flex justify-between">
              <span>{m.model}</span>
              <span className="opacity-70">{(m.pct * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
