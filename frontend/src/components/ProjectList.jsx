import { formatTokens } from "../format.js";
import { useThemeCtx } from "../theme.js";

export default function ProjectList({ projects, selected, onSelect }) {
  const { accent } = useThemeCtx();
  const top5 = projects.slice(0, 5);
  const max = Math.max(1, ...top5.map((p) => p.tokens));
  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] px-6 pt-[22px] pb-[26px] bg-card dark:bg-card-dark">
      <div className="font-bold text-[15px] mb-1">Top projects</div>
      <div className="text-xs text-subtext dark:text-subtext-dark mb-[18px]">by total token count</div>

      {projects.length > 0 && (
        <select
          className="tt-tab w-full mb-4 px-2.5 py-2 border border-border dark:border-border-dark rounded-[9px] text-[13px] font-medium bg-transparent"
          value={selected ?? ""}
          onChange={(e) => onSelect(e.target.value)}
          aria-label="Jump to project"
        >
          <option value="" disabled>
            Jump to project…
          </option>
          {projects.map((p) => (
            <option key={p.project} value={p.project}>
              {p.project} — {formatTokens(p.tokens).abbreviated}
            </option>
          ))}
        </select>
      )}

      <div className="flex flex-col">
        {top5.map((p) => {
          const active = p.project === selected;
          return (
            <div
              key={p.project}
              className={
                "flex flex-col gap-1.5 px-2.5 py-3 rounded-[9px] cursor-pointer" +
                (active ? " bg-pill dark:bg-pill-dark" : "")
              }
              onClick={() => onSelect(p.project)}
              role="button"
              tabIndex={0}
              aria-label={p.project}
              aria-current={active ? "true" : undefined}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(p.project);
                }
              }}
            >
              <div className="flex justify-between items-baseline">
                <span className="font-mono text-[13.5px] font-medium truncate">{p.project}</span>
                <span className="text-xs font-semibold text-subtext dark:text-subtext-dark">
                  {formatTokens(p.tokens).abbreviated}
                </span>
              </div>
              <div className="h-1 rounded-full bg-pill dark:bg-pill-dark">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(p.tokens / max) * 100}%`, background: accent }}
                />
              </div>
            </div>
          );
        })}
        {projects.length === 0 && (
          <p className="text-subtext dark:text-subtext-dark text-sm">No project data yet.</p>
        )}
      </div>
    </div>
  );
}
