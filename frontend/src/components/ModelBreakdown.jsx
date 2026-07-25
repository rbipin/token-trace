import { formatTokens } from "../format.js";
import { useThemeCtx } from "../theme.js";

export default function ModelBreakdown({ summary }) {
  const { accent } = useThemeCtx();
  if (!summary) return null;
  const models = summary.models;
  const max = Math.max(...models.map((m) => m.tokens ?? 0), 1);

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] px-6 pt-[22px] pb-[26px] bg-card dark:bg-card-dark">
      <div className="font-bold text-[15px] mb-3.5">Model breakdown</div>
      <div className="flex flex-col">
        {models.map((m) => (
          <div
            key={m.model}
            className="flex flex-col gap-1.5 py-3 border-b border-border dark:border-border-dark last:border-b-0"
          >
            <div className="flex justify-between items-baseline">
              <span className="font-mono text-[13.5px] font-medium">{m.model}</span>
              <div className="flex gap-[18px] text-xs font-medium text-subtext dark:text-subtext-dark">
                <span>{formatTokens(m.tokens ?? 0).abbreviated}</span>
                <span className="text-fg dark:text-fg-dark font-semibold">
                  {(m.pct * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="h-1 rounded-full bg-pill dark:bg-pill-dark">
              <div
                className="h-full rounded-full"
                style={{ width: `${((m.tokens ?? 0) / max) * 100}%`, background: accent }}
              />
            </div>
          </div>
        ))}
        {models.length === 0 && (
          <p className="text-subtext dark:text-subtext-dark text-sm">No usage data for this range.</p>
        )}
      </div>
    </div>
  );
}
