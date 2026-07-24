export default function HarnessSplit({ summary }) {
  if (!summary) return null;
  return (
    <div className="mb-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Harness split</h4>
      <ul className="space-y-1 text-sm">
        {summary.harnesses.map((h) => (
          <li key={h.source} className="flex items-center gap-2">
            <span className="w-24">{h.source}</span>
            <div className="flex-1 h-2 bg-border dark:bg-border-dark rounded-full overflow-hidden">
              <div className="h-full bg-accent" style={{ width: `${h.pct * 100}%` }} />
            </div>
            <span className="w-12 text-right opacity-70">{(h.pct * 100).toFixed(1)}%</span>
          </li>
        ))}
        {summary.harnesses.length === 0 && <li className="opacity-60">No usage data.</li>}
      </ul>
    </div>
  );
}
