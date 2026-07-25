import { useThemeCtx } from "../theme.js";

const RANGES = ["day", "week", "month", "all"];
const LABELS = { day: "Day", week: "Week", month: "Month", all: "Total" };

export default function RangeTabs({ value, onChange }) {
  const { dark, accent } = useThemeCtx();
  return (
    <div
      className="flex border border-border dark:border-border-dark rounded-[10px] overflow-x-auto tt-scroll max-w-full"
      role="tablist"
      aria-label="Date range"
    >
      {RANGES.map((r) => {
        const active = r === value;
        return (
          <button
            key={r}
            role="tab"
            aria-selected={active}
            className={
              "tt-tab shrink-0 px-[13px] py-[7px] text-xs font-semibold whitespace-nowrap" +
              (active ? "" : " text-subtext dark:text-subtext-dark")
            }
            style={active ? { background: accent, color: dark ? "#07100a" : "#fff" } : undefined}
            onClick={() => onChange(r)}
          >
            {LABELS[r]}
          </button>
        );
      })}
    </div>
  );
}
