export default function ProjectList({ projects, selected, onSelect }) {
  const max = Math.max(1, ...projects.map((p) => p.tokens));
  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Top projects</h4>
      <ul className="space-y-1">
        {projects.map((p) => (
          <li
            key={p.project}
            className={
              (p.project === selected ? "bg-bg dark:bg-bg-dark font-semibold " : "") +
              "p-2 rounded-md cursor-pointer grid grid-cols-[1fr_auto] items-center gap-2"
            }
            onClick={() => onSelect(p.project)}
            role="button"
            tabIndex={0}
            aria-label={p.project}
            aria-current={p.project === selected ? "true" : undefined}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(p.project);
              }
            }}
          >
            <span className="truncate">{p.project}</span>
            <span className="flex items-center gap-2">
              <span className="w-16 h-1.5 bg-border dark:bg-border-dark rounded-full overflow-hidden inline-block">
                <span className="h-full bg-accent block" style={{ width: `${(p.tokens / max) * 100}%` }} />
              </span>
              <small className="opacity-70">{p.tokens.toLocaleString()}</small>
            </span>
          </li>
        ))}
        {projects.length === 0 && <p className="opacity-60">No project data yet.</p>}
      </ul>
    </div>
  );
}
