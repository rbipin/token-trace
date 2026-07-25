import { harnessColor, useThemeCtx } from "../theme.js";

export default function HarnessSplit({ summary }) {
  const { dark, accent } = useThemeCtx();
  if (!summary) return null;
  return (
    <div>
      <div className="text-xs font-semibold tracking-[0.1em] uppercase text-subtext dark:text-subtext-dark mt-6 mb-3">
        Harness split
      </div>
      <div className="flex flex-col gap-2.5">
        {summary.harnesses.map((h) => {
          const color = harnessColor(h.source, dark, dark ? "#8b8d94" : "#78716c", accent);
          return (
            <div key={h.source} className="flex items-center gap-2.5">
              <span
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ background: color }}
              />
              <span className="flex-1 text-[13px] font-medium">{h.source}</span>
              <div className="w-[110px] h-1 rounded-full bg-pill dark:bg-pill-dark overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${h.pct * 100}%`, background: color }}
                />
              </div>
              <span className="font-mono font-semibold text-xs w-[42px] text-right">
                {(h.pct * 100).toFixed(1)}%
              </span>
            </div>
          );
        })}
        {summary.harnesses.length === 0 && (
          <p className="text-subtext dark:text-subtext-dark text-sm">No usage data.</p>
        )}
      </div>
    </div>
  );
}
