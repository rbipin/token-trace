import { harnessIcon, harnessLabel } from "../theme.js";

export default function HarnessCards({ summary }) {
  if (!summary) return null;
  return (
    <div className="flex flex-wrap gap-3 mt-[26px]">
      {summary.harnesses.map((h) => (
        <div
          key={h.source}
          className="flex-1 min-w-[130px] border border-border dark:border-border-dark rounded-[11px] px-[15px] py-3.5 flex flex-col gap-1.5"
        >
          <div className="flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] uppercase text-subtext dark:text-subtext-dark">
            <span>{harnessIcon(h.source)}</span>
            {harnessLabel(h.source)}
          </div>
          <span className="font-bold text-[19px]">{(h.pct * 100).toFixed(1)}%</span>
          <span className="text-[11px] text-subtext dark:text-subtext-dark">
            {h.model_count} model{h.model_count === 1 ? "" : "s"}
          </span>
        </div>
      ))}
      {summary.harnesses.length === 0 && (
        <p className="text-subtext dark:text-subtext-dark text-sm">No usage data for this range.</p>
      )}
    </div>
  );
}
