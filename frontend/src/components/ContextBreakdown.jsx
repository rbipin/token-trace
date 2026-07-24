const COLORS = {
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

  return (
    <div className="mb-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Context breakdown</h4>
      <div className="flex h-2 rounded-full overflow-hidden mb-2">
        {categories.map((c) => (
          <div
            key={c.label}
            style={{ width: `${(c.value / total) * 100}%`, background: COLORS[c.label] }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3 text-xs">
        {categories.map((c) => (
          <span key={c.label} className="flex items-center gap-1">
            <i className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: COLORS[c.label] }} />
            {c.label}: {((c.value / total) * 100).toFixed(1)}% ({c.value.toLocaleString()})
          </span>
        ))}
      </div>
    </div>
  );
}
