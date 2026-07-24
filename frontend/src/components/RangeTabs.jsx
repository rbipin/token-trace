const RANGES = ["day", "week", "month", "all"];
const LABELS = { day: "Day", week: "Week", month: "Month", all: "Total" };

export default function RangeTabs({ value, onChange }) {
  return (
    <div className="flex gap-2" role="tablist" aria-label="Date range">
      {RANGES.map((r) => (
        <button
          key={r}
          role="tab"
          aria-selected={r === value}
          className={
            r === value
              ? "px-3 py-1 rounded-md text-sm font-semibold bg-card dark:bg-card-dark border border-border dark:border-border-dark"
              : "px-3 py-1 rounded-md text-sm border border-transparent opacity-70 hover:opacity-100"
          }
          onClick={() => onChange(r)}
        >
          {LABELS[r]}
        </button>
      ))}
    </div>
  );
}
