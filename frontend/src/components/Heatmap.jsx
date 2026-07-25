import { useEffect, useState } from "react";
import { getHeatmap } from "../api.js";
import { rgba, useThemeCtx } from "../theme.js";

const DAYS_BACK = 180;
const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const LEGEND_STEPS = [0.1, 0.3, 0.55, 0.8, 1];

function toISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// Builds a Sun->Sat, week-per-column calendar covering the last DAYS_BACK
// days, gap-filling any date missing from the API response with 0 tokens,
// and padding the first/last partial weeks with alignment-only placeholders.
function buildWeeks(records, daysBack) {
  const tokensByDate = new Map(records.map((r) => [r.date, r.tokens]));

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const rangeStart = new Date(today);
  rangeStart.setDate(rangeStart.getDate() - (daysBack - 1));

  const gridStart = new Date(rangeStart);
  gridStart.setDate(gridStart.getDate() - gridStart.getDay());

  const gridEnd = new Date(today);
  gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()));

  const cells = [];
  const cursor = new Date(gridStart);
  while (cursor <= gridEnd) {
    const inRange = cursor >= rangeStart && cursor <= today;
    if (inRange) {
      const iso = toISODate(cursor);
      cells.push({ date: iso, tokens: tokensByDate.get(iso) ?? 0, placeholder: false });
    } else {
      cells.push({ date: toISODate(cursor), tokens: 0, placeholder: true });
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }
  return weeks;
}

// One label per week column: the month name is placed on the column
// containing the 1st of that month (GitHub-style), so it stays aligned
// with the day grid below it.
function buildMonthLabels(weeks) {
  return weeks.map((week) => {
    const firstOfMonth = week.find((c) => !c.placeholder && Number(c.date.slice(8, 10)) === 1);
    if (!firstOfMonth) return null;
    const monthIndex = Number(firstOfMonth.date.slice(5, 7)) - 1;
    return MONTH_NAMES[monthIndex];
  });
}

export default function Heatmap({ refreshKey = 0 }) {
  const [days, setDays] = useState([]);
  const { accent } = useThemeCtx();

  useEffect(() => {
    getHeatmap(DAYS_BACK).then(setDays).catch(() => setDays([]));
  }, [refreshKey]);

  const max = days.reduce((m, d) => Math.max(m, d.tokens), 0);
  const weeks = buildWeeks(days, DAYS_BACK);
  const monthLabels = buildMonthLabels(weeks);

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <div className="flex items-center justify-between mb-4">
        <span className="font-bold text-xs tracking-[0.08em] uppercase">Activity heatmap</span>
        <span className="font-mono text-[11px] font-medium text-subtext dark:text-subtext-dark">
          last {DAYS_BACK} days
        </span>
      </div>
      <div className="relative pl-[34px] overflow-x-auto tt-scroll">
        <div className="flex gap-3.5 mb-1.5 pl-[34px]">
          {monthLabels.map((label, i) => (
            <span key={i} className="text-[10.5px] font-medium text-subtext dark:text-subtext-dark w-11 shrink-0">
              {label || ""}
            </span>
          ))}
        </div>
        <div className="flex gap-1.5">
          <div className="flex flex-col gap-1.5 absolute left-0 top-0">
            {DOW_LABELS.map((d) => (
              <span
                key={d}
                className="text-[10px] font-medium text-subtext dark:text-subtext-dark h-[13px] leading-[13px]"
              >
                {d}
              </span>
            ))}
          </div>
          <div
            className="grid gap-1.5"
            style={{
              gridTemplateColumns: `repeat(${weeks.length}, 13px)`,
              gridTemplateRows: "repeat(7, 13px)",
              gridAutoFlow: "column",
            }}
            role="group"
            aria-label={`Daily token activity for the last ${DAYS_BACK} days`}
          >
            {weeks.map((week) =>
              week.map((d) => {
                if (d.placeholder) {
                  return (
                    <div key={d.date} className="w-[13px] h-[13px]" aria-hidden="true" />
                  );
                }
                const hasData = d.tokens > 0;
                const label = `${d.date}: ${d.tokens.toLocaleString()} tokens`;
                let bg = rgba(accent, 0.06);
                let shadow = "none";
                if (hasData) {
                  const norm = Math.pow(d.tokens / (max || 1), 0.55);
                  const a = Math.min(1, 0.16 + 0.84 * norm);
                  bg = rgba(accent, a);
                  shadow = norm > 0.65 ? `0 0 8px ${rgba(accent, 0.4 * norm)}` : "none";
                }
                return (
                  <div
                    key={d.date}
                    role="img"
                    aria-label={label}
                    title={label}
                    tabIndex={0}
                    className="w-[13px] h-[13px] rounded-[3px] focus-visible:outline focus-visible:outline-2"
                    style={{ background: bg, boxShadow: shadow }}
                  />
                );
              })
            )}
          </div>
        </div>
      </div>
      <div className="flex justify-end items-center gap-1.5 mt-3.5 text-[11px] text-subtext dark:text-subtext-dark">
        <span>Less</span>
        {LEGEND_STEPS.map((a, i) => (
          <span
            key={i}
            className="w-[11px] h-[11px] rounded-[2.5px]"
            style={{ background: rgba(accent, 0.14 + 0.86 * a) }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}
