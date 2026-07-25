import { formatTokens } from "../format.js";

export const COLORS = {
  Input: "#22c55e",
  Output: "#5b8def",
  "Cache Read": "#a78bfa",
  "Cache Creation": "#f2994a",
  Reasoning: "#f1c40f",
};

export default function ContextBreakdown({ summary }) {
  if (!summary) return null;
  const categories = [
    { label: "Input", value: summary.input_tokens },
    { label: "Output", value: summary.output_tokens },
    { label: "Cache Read", value: summary.cache_read_tokens },
    { label: "Cache Creation", value: summary.cache_creation_tokens },
    { label: "Reasoning", value: summary.reasoning_tokens },
  ];
  const total = categories.reduce((sum, c) => sum + c.value, 0) || 1;
  const maxVal = Math.max(...categories.map((c) => c.value), 1);

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] px-[26px] pt-[22px] pb-[26px] bg-card dark:bg-card-dark">
      <div className="font-bold text-[15px] mb-3.5">✳ Context breakdown</div>
      <div className="flex flex-col gap-2.5">
        {categories.map((c) => (
          <div key={c.label} className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: COLORS[c.label] }} />
              <span className="flex-1 text-[13.5px] font-medium">{c.label}</span>
              <span className="font-mono font-semibold text-[12.5px]">
                {formatTokens(c.value).abbreviated}
              </span>
              <span className="text-[11.5px] font-medium text-subtext dark:text-subtext-dark w-11 text-right">
                {((c.value / total) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-1 rounded-full bg-pill dark:bg-pill-dark">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.max(2, (c.value / maxVal) * 100)}%`, background: COLORS[c.label] }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
