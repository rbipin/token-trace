import { formatTokens } from "../format.js";

function Pill({ value, label }) {
  return (
    <div className="flex flex-col items-center gap-0.5 py-2.5 px-1 rounded-[10px] bg-pill dark:bg-pill-dark">
      <span className="font-bold text-base">{value}</span>
      <span className="text-[10px] font-medium text-subtext dark:text-subtext-dark">{label}</span>
    </div>
  );
}

export default function StatsRow({ summary }) {
  if (!summary) {
    return (
      <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark text-subtext dark:text-subtext-dark text-sm">
        Loading…
      </div>
    );
  }
  const rolling = summary.rolling;
  const pills = [
    { value: formatTokens(rolling["7d"].total_tokens).abbreviated, label: "7d" },
    { value: formatTokens(rolling["30d"].total_tokens).abbreviated, label: "30d" },
    { value: formatTokens(Math.round(rolling.avg_per_active_day)).abbreviated, label: "avg" },
    { value: formatTokens(rolling.month.total_tokens).abbreviated, label: "month" },
  ];

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <div className="grid grid-cols-4 gap-2">
        {pills.map((p) => (
          <Pill key={p.label} {...p} />
        ))}
      </div>
      <div className="flex flex-col gap-3 mt-[18px]">
        {summary.models.slice(0, 3).map((m, i) => (
          <div key={m.model} className="flex items-center gap-3">
            <span className="font-mono font-semibold text-xs text-subtext dark:text-subtext-dark w-3.5">
              {i + 1}
            </span>
            <span className="flex-1 text-[13.5px] font-medium truncate">{m.model}</span>
            <span className="font-mono font-semibold text-[13px]">{(m.pct * 100).toFixed(1)}%</span>
          </div>
        ))}
        {summary.models.length === 0 && (
          <p className="text-subtext dark:text-subtext-dark text-sm">No usage data for this range.</p>
        )}
      </div>
      <div className="flex justify-between mt-[18px] pt-3.5 border-t border-border dark:border-border-dark text-[11.5px] font-medium text-subtext dark:text-subtext-dark">
        <span>Started {summary.first_date || "—"}</span>
        <span>Active days {summary.active_days}</span>
      </div>
    </div>
  );
}
