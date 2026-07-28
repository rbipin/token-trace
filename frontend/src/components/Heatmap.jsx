import { useEffect, useRef, useState } from "react";
import { getHeatmap } from "../api.js";
import { rgba, useThemeCtx } from "../theme.js";

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

// Builds a Sun->Sat, week-per-column calendar covering [rangeStart, rangeEnd],
// gap-filling any date missing from the API response with 0 tokens. Days after
// today render as empty "future" cells; days outside the range pad the
// first/last weeks as invisible placeholders.
function buildWeeks(records, rangeStart, rangeEnd) {
  const tokensByDate = new Map(records.map((r) => [r.date, r.tokens]));

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const gridStart = new Date(rangeStart);
  gridStart.setDate(gridStart.getDate() - gridStart.getDay());

  const gridEnd = new Date(rangeEnd);
  gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()));

  const cells = [];
  const cursor = new Date(gridStart);
  while (cursor <= gridEnd) {
    const iso = toISODate(cursor);
    const inRange = cursor >= rangeStart && cursor <= rangeEnd;
    cells.push({
      date: iso,
      tokens: inRange ? tokensByDate.get(iso) ?? 0 : 0,
      placeholder: !inRange,
      future: inRange && cursor > today,
    });
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

// Days elapsed in the current year (Jan 1 -> today, inclusive). The API
// lookback is the max of this and 90 days so the compact (last-90-days)
// view still has data early in the year.
function daysSinceYearStart() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yearStart = new Date(today.getFullYear(), 0, 1);
  return Math.round((today - yearStart) / 86400000) + 1;
}

const MAX_CELL = 13;
const MIN_CELL = 8;
const GAP_RATIO = 6 / 13;
const LABEL_COL = 30;

// Largest cell size (px) at which `weekCount` columns fit in `width`.
function fitCell(width, weekCount) {
  const avail = width - LABEL_COL - 6;
  return Math.floor(avail / weekCount / (1 + GAP_RATIO));
}

export default function Heatmap({ refreshKey = 0 }) {
  const [days, setDays] = useState([]);
  const [width, setWidth] = useState(0);
  const containerRef = useRef(null);
  const { accent } = useThemeCtx();

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const year = today.getFullYear();

  useEffect(() => {
    getHeatmap(Math.max(daysSinceYearStart(), 190)).then(setDays).catch(() => setDays([]));
  }, [refreshKey]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const max = days.reduce((m, d) => Math.max(m, d.tokens), 0);

  // Prefer the full Jan-Dec year, scaling cells down to fit the container.
  // If cells would drop below MIN_CELL, fall back to a compact window: the
  // last 3 calendar months (including the current one) plus the next month.
  const yearStart = new Date(year, 0, 1);
  const yearEnd = new Date(year, 11, 31);
  const fullWeekCount = Math.ceil(
    (Math.round((yearEnd - yearStart) / 86400000) + yearStart.getDay() + 1) / 7
  );
  const compact = width > 0 && fitCell(width, fullWeekCount) < MIN_CELL;

  const compactStart = new Date(today.getFullYear(), today.getMonth() - 2, 1);
  const compactEnd = new Date(today.getFullYear(), today.getMonth() + 2, 0);
  const rangeStart = compact ? compactStart : yearStart;
  const rangeEnd = compact ? compactEnd : yearEnd;
  const compactLabel = `${MONTH_NAMES[compactStart.getMonth()]} – ${MONTH_NAMES[compactEnd.getMonth()]}`;

  const weeks = buildWeeks(days, rangeStart, rangeEnd);
  const monthLabels = buildMonthLabels(weeks);

  const cell = width > 0
    ? Math.max(6, Math.min(MAX_CELL, fitCell(width, weeks.length)))
    : MAX_CELL;
  const gap = Math.max(2, Math.round(cell * GAP_RATIO));
  const cellPx = `${cell}px`;

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <div className="flex items-center justify-between mb-4">
        <span className="font-bold text-xs tracking-[0.08em] uppercase">Activity heatmap</span>
        <span className="font-mono text-[11px] font-medium text-subtext dark:text-subtext-dark">
          {compact ? compactLabel : year}
        </span>
      </div>
      <div ref={containerRef} className="overflow-x-auto tt-scroll">
        <div className="flex" style={{ gap }}>
          <div className="flex flex-col shrink-0 w-[30px]" style={{ gap }}>
            <span className="h-[16px]" aria-hidden="true" />
            {DOW_LABELS.map((d, i) => (
              <span
                key={d}
                className="text-[10px] font-medium text-subtext dark:text-subtext-dark"
                style={{ height: cellPx, lineHeight: cellPx }}
              >
                {cell >= 10 || i % 2 === 1 ? d : ""}
              </span>
            ))}
          </div>
          <div>
            <div
              className="grid h-[16px] mb-1.5"
              style={{ gap, gridTemplateColumns: `repeat(${weeks.length}, ${cellPx})` }}
            >
              {monthLabels.map((label, i) =>
                label ? (
                  <span
                    key={i}
                    className="text-[10.5px] font-medium text-subtext dark:text-subtext-dark whitespace-nowrap overflow-visible"
                    style={{ gridColumnStart: i + 1 }}
                  >
                    {label}
                  </span>
                ) : null
              )}
            </div>
            <div
              className="grid"
              style={{
                gap,
                gridTemplateColumns: `repeat(${weeks.length}, ${cellPx})`,
                gridTemplateRows: `repeat(7, ${cellPx})`,
                gridAutoFlow: "column",
              }}
              role="group"
              aria-label={compact
                ? `Daily token activity, ${compactLabel}`
                : `Daily token activity for ${year}`}
            >
              {weeks.map((week) =>
              week.map((d) => {
                if (d.placeholder) {
                  return (
                    <div key={d.date} style={{ width: cellPx, height: cellPx }} aria-hidden="true" />
                  );
                }
                if (d.future) {
                  return (
                    <div
                      key={d.date}
                      className="rounded-[3px]"
                      style={{ width: cellPx, height: cellPx, background: rgba(accent, 0.03) }}
                      aria-hidden="true"
                    />
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
                    className="rounded-[3px] focus-visible:outline focus-visible:outline-2"
                    style={{ width: cellPx, height: cellPx, background: bg, boxShadow: shadow }}
                  />
                );
              })
            )}
            </div>
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
