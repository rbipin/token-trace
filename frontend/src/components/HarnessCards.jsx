export default function HarnessCards({ summary }) {
  if (!summary) return null;
  return (
    <div className="mt-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {summary.harnesses.map((h) => (
          <div
            key={h.source}
            className="bg-bg dark:bg-bg-dark border border-border dark:border-border-dark rounded-lg p-3 flex flex-col gap-1"
          >
            <strong className="text-sm">{h.source}</strong>
            <span className="text-lg font-semibold text-accent">{(h.pct * 100).toFixed(1)}%</span>
            <small className="opacity-60">{h.model_count} model{h.model_count === 1 ? "" : "s"}</small>
          </div>
        ))}
        {summary.harnesses.length === 0 && <p className="opacity-60">No usage data for this range.</p>}
      </div>
    </div>
  );
}
