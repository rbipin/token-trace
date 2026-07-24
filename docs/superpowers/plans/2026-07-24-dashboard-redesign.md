# Dashboard Redesign ("Token Trace") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the existing dashboard (`src/dashboard/` + `frontend/`) to match the "Token Trace" visual design (`docs/design/dashboard.html`), per `docs/superpowers/specs/2026-07-24-dashboard-redesign-design.md`.

**Architecture:** This is a layout-and-visual redesign of an already-working app, not a rebuild. One backend addition (a `rolling` stats block on `summary()`) supports the fixed rolling-stat row; everything else is a Tailwind-CSS-driven restructure of existing React components, most of which already have the right data shape.

**Tech Stack:** Python stdlib (backend, unchanged), React 18 + Vite 5 (existing), Tailwind CSS v4 via `@tailwindcss/vite` (new).

## Global Constraints

- Range tabs: **Day / Week / Month / Total** only, backed by the `day`/`week`/`month`/`all` periods already in `src/dashboard/queries.py`. No Custom tab, no date-range picker — remove the existing custom-range UI entirely.
- The rolling-stat row (7d / 30d / avg-per-active-day / month totals, "Started" date, "Active days" count) is **fixed** — always shows these regardless of the selected range tab.
- Model breakdown: the top-left short model list (top-5 by %, in the same card as the rolling stats) is the **only** model view. No standalone full model table anywhere on the page — `ModelTable.jsx` is deleted.
- The segmented bar under the hero "Total Tokens" number represents **Context Breakdown** using the actual collected token categories — Input / Output / Cache Read / Cache Creation / Reasoning (the existing `summary()` fields) — not harness split and not the mockup's fictional categories (Messages/System prompt/Custom agents/MCP servers/Skills, which have no backing data and are not used).
- Harness split (percentage by source) is shown separately — as icon+percentage cards on the Tokens page, and as a percentage list on the By Project detail panel — never as a segmented bar (that visual is reserved for Context Breakdown).
- Out of scope, not built even as disabled placeholders: "Limits" sidebar nav item, "Share" header button, custom date-range picking.
- No new pages beyond the existing Tokens and By Project pages.
- Dark palette: page background `#0a0b0d`, card background `#12141a`, border `#2a2e3a`, text `#e6e8ef`, accent green `#22c55e`, accent purple `#a78bfa`. Light palette (baseline, unchanged): background `#f5f6f8`, card `#ffffff`, border `#dfe1e6`, text `#1a1c22`.
- The existing `data-theme="dark"|"light"` toggle on `<html>` is preserved; dark styling is expressed via Tailwind's `dark:` variant, retargeted to match on `[data-theme="dark"]` instead of `prefers-color-scheme`.
- Frontend has no JS test suite (stdlib-only project) — frontend tasks are verified manually via `npm run dev` and comparison against `docs/design/dashboard.html`, per the spec's Testing section.

---

## Task 1: Backend — rolling stats block on `summary()`

**Files:**
- Modify: `src/dashboard/queries.py`
- Test: `tests/test_dashboard_queries.py`

**Interfaces:**
- Produces: `summary(...)` return dict gains a `"rolling"` key:
  ```python
  {
      "7d": {"total_tokens": int},
      "30d": {"total_tokens": int, "active_days": int},
      "month": {"total_tokens": int},
      "avg_per_active_day": float,  # 30d total_tokens / 30d active_days, 0.0 if active_days == 0
  }
  ```
  Computed independently of the `period` argument (always true last-7-days / last-30-days / calendar-month-to-date), but still respects the `project`/`source` filters passed to `summary()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_dashboard_queries.py` (add `timedelta` to the existing `from datetime import date` import at the top of the file):

```python
from datetime import date, timedelta
```

Add these three tests after `test_summary_totals_and_harnesses`:

```python
def test_summary_rolling_totals(tmp_db):
    store = SqliteStore(tmp_db)
    today = date.today()
    d0 = today.isoformat()
    d5 = (today - timedelta(days=5)).isoformat()
    d20 = (today - timedelta(days=20)).isoformat()
    d40 = (today - timedelta(days=40)).isoformat()
    store.upsert([
        _rec("s1", d0, input_tokens=100),
        _rec("s2", d5, input_tokens=50),
        _rec("s3", d20, input_tokens=200),
        _rec("s4", d40, input_tokens=999),
    ])
    rolling = queries.summary(_conn(tmp_db), "all")["rolling"]
    assert rolling["7d"]["total_tokens"] == 150
    assert rolling["30d"]["total_tokens"] == 350
    assert rolling["30d"]["active_days"] == 3
    assert round(rolling["avg_per_active_day"], 4) == round(350 / 3, 4)


def test_summary_rolling_zero_active_days(tmp_db):
    result = queries.summary(_conn(tmp_db), "all")
    assert result["rolling"]["30d"]["active_days"] == 0
    assert result["rolling"]["avg_per_active_day"] == 0.0
    assert result["rolling"]["7d"]["total_tokens"] == 0
    assert result["rolling"]["month"]["total_tokens"] == 0


def test_summary_rolling_respects_project_filter(tmp_db):
    store = SqliteStore(tmp_db)
    today = date.today().isoformat()
    store.upsert([
        _rec("s1", today, input_tokens=100, project="proj-a"),
        _rec("s2", today, input_tokens=300, project="proj-b"),
    ])
    result = queries.summary(_conn(tmp_db), "all", project="proj-a")
    assert result["rolling"]["7d"]["total_tokens"] == 100


def test_summary_rolling_independent_of_period(tmp_db):
    """rolling must reflect real last-7d/30d/month windows, not the period filter."""
    store = SqliteStore(tmp_db)
    today = date.today().isoformat()
    store.upsert([_rec("s1", today, input_tokens=100)])
    result = queries.summary(_conn(tmp_db), "day")
    assert result["rolling"]["7d"]["total_tokens"] == 100
    assert result["rolling"]["30d"]["total_tokens"] == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_dashboard_queries.py -k rolling -v`
Expected: FAIL with `KeyError: 'rolling'`

- [ ] **Step 3: Implement the rolling stats helper and wire it into `summary()`**

In `src/dashboard/queries.py`, add a helper function above `summary()`:

```python
def _rolling_stats(conn: sqlite3.Connection, extra: str, params: list) -> dict:
    def window(where: str, wparams: list) -> tuple[int, int]:
        row = conn.execute(f"""
            SELECT COALESCE(SUM({_TOKENS_EXPR}), 0) AS tokens,
                   COUNT(DISTINCT date) AS active_days
            FROM sessions
            WHERE {where}{extra}
        """, wparams + params).fetchone()
        return row["tokens"], row["active_days"]

    tokens_7d, _ = window(*_last_n_days_filter(7))
    tokens_30d, active_days_30d = window(*_last_n_days_filter(30))
    tokens_month, _ = window(_DATE_RANGE_SQL["month"], [])
    avg = (tokens_30d / active_days_30d) if active_days_30d else 0.0

    return {
        "7d": {"total_tokens": tokens_7d},
        "30d": {"total_tokens": tokens_30d, "active_days": active_days_30d},
        "month": {"total_tokens": tokens_month},
        "avg_per_active_day": avg,
    }
```

In `summary()`, after the `totals = conn.execute(...)` block (which already builds `extra`/`params` from `project`/`source`), add:

```python
    rolling = _rolling_stats(conn, extra, params)
```

Then add `"rolling": rolling,` to the returned dict (alongside `"harnesses"` and `"models"`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_dashboard_queries.py -v`
Expected: all tests PASS, including the 4 new rolling tests and all pre-existing ones.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/queries.py tests/test_dashboard_queries.py
git commit -m "feat(dashboard): add rolling 7d/30d/month stats to summary()"
```

---

## Task 2: Frontend — add Tailwind CSS to the Vite build

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Produces: Tailwind utility classes usable in JSX; `dark:` variant matches `[data-theme="dark"]` (not `prefers-color-scheme`); theme colors available as `bg-bg`/`bg-bg-dark`/`bg-card`/`bg-card-dark`/`border-border`/`border-border-dark`/`text-fg`/`text-fg-dark`/`bg-accent`/`bg-accent-purple`.
- Existing hand-written CSS classes (`.card`, `.grid-2`, `.heatmap-*`, `.segmented-bar`, `.harness-*`, `.range-tabs`, `.bar-*`, `.model-table`, `.project-list`) are left in place for now — later tasks migrate each one to Tailwind utilities and delete the corresponding rule (Task 12 confirms none remain).

- [ ] **Step 1: Install Tailwind CSS v4 and its Vite plugin**

Run: `cd frontend && npm install -D tailwindcss @tailwindcss/vite`
Expected: `frontend/package.json` `devDependencies` gains `tailwindcss` and `@tailwindcss/vite` entries; `frontend/package-lock.json` is created/updated.

- [ ] **Step 2: Register the Tailwind Vite plugin**

Modify `frontend/vite.config.js`:

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8420",
    },
  },
});
```

- [ ] **Step 3: Add the Tailwind import, custom dark variant, and theme tokens**

At the very top of `frontend/src/App.css`, before the existing `:root[data-theme="dark"]` block, insert:

```css
@import "tailwindcss";

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@theme {
  --color-bg: #f5f6f8;
  --color-card: #ffffff;
  --color-border: #dfe1e6;
  --color-fg: #1a1c22;
  --color-bg-dark: #0a0b0d;
  --color-card-dark: #12141a;
  --color-border-dark: #2a2e3a;
  --color-fg-dark: #e6e8ef;
  --color-accent: #22c55e;
  --color-accent-purple: #a78bfa;
}
```

Leave the rest of the existing `App.css` file (the `:root[data-theme=...]` blocks and all `.card`/`.grid-2`/etc. rules) untouched for now — they still style the app until later tasks migrate each component.

- [ ] **Step 4: Verify manually**

Run: `cd frontend && npm run dev`
Expected: Vite starts without errors; open the printed local URL (e.g. `http://localhost:5173`) — the app renders exactly as before (old CSS still active), confirming the Tailwind build step doesn't break anything.

Run: `cd frontend && npm run build`
Expected: build succeeds with no Tailwind/PostCSS errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/src/App.css
git commit -m "build(dashboard): add Tailwind CSS v4 to the frontend Vite build"
```

---

## Task 3: Frontend — shared `formatTokens` and `formatRelativeTime` helpers

**Files:**
- Create: `frontend/src/format.js`
- Create: `frontend/src/relativeTime.js`

**Interfaces:**
- Produces: `formatTokens(value: number) -> { full: string, abbreviated: string }` — `full` is `value.toLocaleString()`, `abbreviated` is a `K`/`M`/`B`-suffixed short form.
- Produces: `formatRelativeTime(isoTimestamp: string | null) -> string` — `"—"` for falsy input, else `"just now"` / `"Nm ago"` / `"Nh ago"` / `"Nd ago"`.

- [ ] **Step 1: Write `frontend/src/format.js`**

```js
export function formatTokens(value) {
  const n = value || 0;
  return { full: n.toLocaleString(), abbreviated: abbreviate(n) };
}

function abbreviate(n) {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return String(n);
}
```

- [ ] **Step 2: Verify `formatTokens` manually**

Run: `cd frontend && node --input-type=module -e "import { formatTokens } from './src/format.js'; console.log(formatTokens(263700000000)); console.log(formatTokens(950)); console.log(formatTokens(0));"`
Expected output:
```
{ full: '263,700,000,000', abbreviated: '263.7B' }
{ full: '950', abbreviated: '950' }
{ full: '0', abbreviated: '0' }
```

- [ ] **Step 3: Write `frontend/src/relativeTime.js`**

```js
export function formatRelativeTime(isoTimestamp) {
  if (!isoTimestamp) return "—";
  const then = new Date(isoTimestamp).getTime();
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}
```

- [ ] **Step 4: Verify `formatRelativeTime` manually**

Run: `cd frontend && node --input-type=module -e "
import { formatRelativeTime } from './src/relativeTime.js';
console.log(formatRelativeTime(null));
console.log(formatRelativeTime(new Date(Date.now() - 5 * 60000).toISOString()));
console.log(formatRelativeTime(new Date(Date.now() - 3 * 3600000).toISOString()));
"`
Expected output:
```
—
5m ago
3h ago
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/format.js frontend/src/relativeTime.js
git commit -m "feat(dashboard): add formatTokens and formatRelativeTime helpers"
```

---

## Task 4: Frontend — `RangeTabs.jsx`, remove custom date-range picker

**Files:**
- Create: `frontend/src/components/RangeTabs.jsx`
- Modify: `frontend/src/pages/TokensPage.jsx`
- Modify: `frontend/src/App.css` (remove `.range-tabs` rule, now replaced by Tailwind classes in `RangeTabs.jsx`)

**Interfaces:**
- Produces: `RangeTabs({ value, onChange })` — controlled component; `value` is one of `"day" | "week" | "month" | "all"`; calls `onChange(nextValue)` on click.

- [ ] **Step 1: Write `frontend/src/components/RangeTabs.jsx`**

```jsx
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
```

- [ ] **Step 2: Replace the inline range-tabs/custom-range UI in `TokensPage.jsx`**

Modify `frontend/src/pages/TokensPage.jsx` — replace the whole file with:

```jsx
import { useEffect, useState } from "react";
import { getSummary } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsCard from "../components/StatsCard.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import ModelTable from "../components/ModelTable.jsx";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRefreshKey((k) => k + 1);
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range]);

  return (
    <div>
      <RangeTabs value={range} onChange={setRange} />
      <div className="grid-2">
        <StatsCard summary={summary} />
        <SyncLogCard refreshKey={refreshKey} />
      </div>
      <Heatmap refreshKey={refreshKey} />
      <TrendChart refreshKey={refreshKey} />
      <div className="card">
        <h3>{summary ? summary.total_tokens.toLocaleString() : "—"} tokens</h3>
        <HarnessCards summary={summary} />
      </div>
      <ContextBreakdown summary={summary} />
      <ModelTable summary={summary} />
    </div>
  );
}
```

(This is an intermediate state — `StatsCard`/`ModelTable` are replaced in Task 5, and the hero/badge layout is finished in Task 7. This step's only job is removing the custom-range picker and extracting `RangeTabs`.)

- [ ] **Step 3: Remove the now-unused `.range-tabs` rule from `App.css`**

Delete this line from `frontend/src/App.css`:
```css
.range-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.range-tabs button { padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: none; color: var(--text); cursor: pointer; }
.range-tabs button.active { background: var(--card-bg); font-weight: 600; }
```

- [ ] **Step 4: Verify manually**

Run: `cd frontend && npm run dev`, open the Tokens page. Expected: four tabs (Day/Week/Month/Total) render, clicking each changes the displayed data (check the Network tab or the stats card numbers), no date-range inputs appear anywhere.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RangeTabs.jsx frontend/src/pages/TokensPage.jsx frontend/src/App.css
git commit -m "feat(dashboard): extract RangeTabs component, drop custom date-range picker"
```

---

## Task 5: Frontend — `StatsRow.jsx` (rolling stats + top models), delete `StatsCard.jsx` and `ModelTable.jsx`

**Files:**
- Create: `frontend/src/components/StatsRow.jsx`
- Delete: `frontend/src/components/StatsCard.jsx`
- Delete: `frontend/src/components/ModelTable.jsx`
- Modify: `frontend/src/pages/TokensPage.jsx`
- Modify: `frontend/src/App.css` (remove `.model-table` rule)

**Interfaces:**
- Consumes: `summary().rolling` (Task 1), `summary().active_days`, `summary().first_date`, `summary().models` (existing).
- Produces: `StatsRow({ summary })` — renders 7d/30d/avg/month/Started/Active-days stats plus the top-5 model list. This is the **only** place models are shown anywhere on the page.

- [ ] **Step 1: Write `frontend/src/components/StatsRow.jsx`**

```jsx
import { formatTokens } from "../format.js";

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs opacity-60">{label}</div>
    </div>
  );
}

export default function StatsRow({ summary }) {
  if (!summary) {
    return (
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
        Loading…
      </div>
    );
  }
  const rolling = summary.rolling;
  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-4">
        <Stat label="Last 7d" value={formatTokens(rolling["7d"].total_tokens).abbreviated} />
        <Stat label="Last 30d" value={formatTokens(rolling["30d"].total_tokens).abbreviated} />
        <Stat label="Avg/active day" value={formatTokens(Math.round(rolling.avg_per_active_day)).abbreviated} />
        <Stat label="This month" value={formatTokens(rolling.month.total_tokens).abbreviated} />
        <Stat label="Started" value={summary.first_date || "—"} />
        <Stat label="Active days" value={summary.active_days} />
      </div>
      <div>
        <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Top models</h4>
        <ol className="space-y-1 text-sm">
          {summary.models.slice(0, 5).map((m) => (
            <li key={m.model} className="flex justify-between">
              <span>{m.model}</span>
              <span className="opacity-70">{(m.pct * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Delete the old components**

```bash
git rm frontend/src/components/StatsCard.jsx frontend/src/components/ModelTable.jsx
```

- [ ] **Step 3: Wire `StatsRow` into `TokensPage.jsx`, remove `ModelTable`**

Replace `frontend/src/pages/TokensPage.jsx` with:

```jsx
import { useEffect, useState } from "react";
import { getSummary } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsRow from "../components/StatsRow.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRefreshKey((k) => k + 1);
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range]);

  return (
    <div>
      <RangeTabs value={range} onChange={setRange} />
      <div className="grid-2">
        <StatsRow summary={summary} />
        <SyncLogCard refreshKey={refreshKey} />
      </div>
      <Heatmap refreshKey={refreshKey} />
      <TrendChart refreshKey={refreshKey} />
      <div className="card">
        <h3>{summary ? summary.total_tokens.toLocaleString() : "—"} tokens</h3>
        <HarnessCards summary={summary} />
      </div>
      <ContextBreakdown summary={summary} />
    </div>
  );
}
```

- [ ] **Step 4: Remove the now-unused `.model-table` rule from `App.css`**

Delete this line from `frontend/src/App.css`:
```css
.model-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.model-table th, .model-table td { text-align: left; padding: 6px 4px; border-bottom: 1px solid var(--border); }
```

- [ ] **Step 5: Verify manually**

Run: `cd frontend && npm run dev`, open the Tokens page. Expected: one card shows 7d/30d/avg/month/Started/Active-days numbers plus a top-5 model list; there is no second "Model breakdown" table anywhere on the page.

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src/components frontend/src/pages/TokensPage.jsx frontend/src/App.css
git commit -m "feat(dashboard): replace StatsCard/ModelTable with StatsRow, drop bottom model table"
```

---

## Task 6: Frontend — `App.jsx` sidebar branding restyle

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.css` (remove `.sidebar`/`.nav-*`/`.theme-toggle`/`.page-header` rules, now replaced by Tailwind classes)

**Interfaces:**
- Produces: no prop/behavior changes — same `page`/`theme` state and `data-theme` attribute mechanism. The global "Most recent data" header is removed here (it moves into `TokensPage` in Task 7).

- [ ] **Step 1: Rewrite `App.jsx`**

```jsx
import { useEffect, useState } from "react";
import TokensPage from "./pages/TokensPage.jsx";
import ProjectsPage from "./pages/ProjectsPage.jsx";
import "./App.css";

export default function App() {
  const [page, setPage] = useState("tokens");
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <div className="flex min-h-screen bg-bg dark:bg-bg-dark text-fg dark:text-fg-dark">
      <nav className="w-52 p-4 border-r border-border dark:border-border-dark flex flex-col gap-2">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-6 h-6 rounded bg-accent" />
          <span className="font-semibold">Token Trace</span>
        </div>
        <button
          className={
            page === "tokens"
              ? "text-left px-3 py-2 rounded-md bg-card dark:bg-card-dark font-semibold"
              : "text-left px-3 py-2 rounded-md opacity-70 hover:opacity-100"
          }
          onClick={() => setPage("tokens")}
        >
          Tokens
        </button>
        <button
          className={
            page === "projects"
              ? "text-left px-3 py-2 rounded-md bg-card dark:bg-card-dark font-semibold"
              : "text-left px-3 py-2 rounded-md opacity-70 hover:opacity-100"
          }
          onClick={() => setPage("projects")}
        >
          By Project
        </button>
        <button
          className="mt-auto text-left px-3 py-2 rounded-md border border-border dark:border-border-dark"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </nav>
      <main className="flex-1 p-6">
        {page === "tokens" ? <TokensPage /> : <ProjectsPage />}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Remove the now-unused sidebar/header rules from `App.css`**

Delete these lines from `frontend/src/App.css`:
```css
.app { display: flex; min-height: 100vh; }
.sidebar { width: 200px; padding: 16px; border-right: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
.nav-group { font-size: 12px; text-transform: uppercase; opacity: 0.6; margin-bottom: 8px; }
.nav-item, .theme-toggle { background: none; border: none; color: var(--text); text-align: left; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
.nav-item.active { background: var(--card-bg); font-weight: 600; }
.theme-toggle { margin-top: auto; border: 1px solid var(--border); }
.content { flex: 1; padding: 24px; }
.page-header { display: flex; justify-content: flex-end; font-size: 13px; opacity: 0.7; margin-bottom: 16px; }
```

- [ ] **Step 3: Verify manually**

Run: `cd frontend && npm run dev`. Expected: sidebar shows the green square logo mark + "Token Trace" wordmark, Tokens/By Project nav items, and a light/dark toggle at the bottom; switching pages and toggling theme both still work; the top-right "Most recent data" text is gone (added back on the Tokens page in Task 7).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.css
git commit -m "feat(dashboard): restyle sidebar with Token Trace branding"
```

---

## Task 7: Frontend — `TokensPage.jsx` hero number, "most recent data" badge, final wiring

**Files:**
- Modify: `frontend/src/pages/TokensPage.jsx`
- Modify: `frontend/src/App.css` (remove `.grid-2` rule)

**Interfaces:**
- Consumes: `getMeta()` (existing `frontend/src/api.js`), `formatTokens` and `formatRelativeTime` (Task 3).
- Produces: no new exports — this is the page's final layout for this redesign (hero total + badge above; stats/sync row; heatmap/trend; hero-tokens card with context breakdown + harness cards).

- [ ] **Step 1: Rewrite `TokensPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { getSummary, getMeta } from "../api.js";
import RangeTabs from "../components/RangeTabs.jsx";
import StatsRow from "../components/StatsRow.jsx";
import SyncLogCard from "../components/SyncLogCard.jsx";
import Heatmap from "../components/Heatmap.jsx";
import TrendChart from "../components/TrendChart.jsx";
import HarnessCards from "../components/HarnessCards.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import { formatTokens } from "../format.js";
import { formatRelativeTime } from "../relativeTime.js";

export default function TokensPage() {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState("all");
  const [mostRecent, setMostRecent] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRefreshKey((k) => k + 1);
    getSummary({ period: range }).then(setSummary).catch(() => {});
  }, [range]);

  useEffect(() => {
    getMeta().then((data) => setMostRecent(data.most_recent_data_at)).catch(() => {});
  }, [refreshKey]);

  const tokens = summary ? formatTokens(summary.total_tokens) : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <RangeTabs value={range} onChange={setRange} />
        <span className="text-xs opacity-60">
          Most recent data: {mostRecent ? formatRelativeTime(mostRecent) : "—"}
        </span>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <StatsRow summary={summary} />
        <SyncLogCard refreshKey={refreshKey} />
      </div>
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-6 mb-4">
        <h2 className="text-4xl font-semibold mb-1">{tokens ? tokens.full : "—"}</h2>
        <p className="text-xs uppercase tracking-wide opacity-60 mb-4">Total tokens</p>
        <ContextBreakdown summary={summary} />
        <HarnessCards summary={summary} />
      </div>
      <Heatmap refreshKey={refreshKey} />
      <TrendChart refreshKey={refreshKey} />
    </div>
  );
}
```

- [ ] **Step 2: Remove the now-unused `.grid-2` rule from `App.css`**

Delete this line from `frontend/src/App.css`:
```css
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
```

- [ ] **Step 3: Verify manually**

Run: `cd frontend && npm run dev`. Expected: top row shows range tabs (left) and "Most recent data: Xm ago" (right); below it, the stats/sync-log row; below that, a card with a large comma-formatted total-tokens number, the context-breakdown bar, and harness cards; heatmap and trend chart below that. Switching range tabs changes the hero number, context breakdown, and harness cards, but not the stats row (7d/30d/month/avg stay fixed).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TokensPage.jsx frontend/src/App.css
git commit -m "feat(dashboard): add hero total-tokens number and most-recent-data badge to Tokens page"
```

---

## Task 8: Frontend — `HarnessCards.jsx` restyle (drop its segmented bar)

**Files:**
- Modify: `frontend/src/components/HarnessCards.jsx`
- Modify: `frontend/src/App.css` (remove `.segmented-bar`/`.segment`/`.harness-*` rules)

**Interfaces:**
- Consumes: `summary().harnesses` (unchanged shape: `{ source, tokens, model_count, pct }[]`).
- Produces: `HarnessCards({ summary })` — same prop, renders only the icon+percentage grid now (the harness-level segmented bar it used to render is removed; the page's single segmented bar is `ContextBreakdown`'s, per Global Constraints).

- [ ] **Step 1: Rewrite `HarnessCards.jsx`**

```jsx
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
```

- [ ] **Step 2: Remove the now-unused rules from `App.css`**

Delete these lines from `frontend/src/App.css`:
```css
.segmented-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--border); margin-bottom: 12px; }
.segment { background: #5b8def; border-right: 1px solid var(--bg); }
.harness-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
.harness-card { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
```

- [ ] **Step 3: Verify manually**

Run: `cd frontend && npm run dev`, open the Tokens page. Expected: harness cards render as a grid with green percentage numbers; there is no separate thin segmented bar above the harness grid (only the one segmented bar from `ContextBreakdown`, above it).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/HarnessCards.jsx frontend/src/App.css
git commit -m "style(dashboard): restyle HarnessCards, drop its duplicate segmented bar"
```

---

## Task 9: Frontend — `ContextBreakdown.jsx` restyle (segmented gradient bar + legend)

**Files:**
- Modify: `frontend/src/components/ContextBreakdown.jsx`
- Modify: `frontend/src/App.css` (remove `.bar-row`/`.bar-track`/`.bar-fill`/`.legend*` rules — re-check Task 10/11 before deleting `.bar-track`/`.bar-fill` since `ProjectList.jsx` also uses them; see Step 2)

**Interfaces:**
- Consumes: `summary().input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `reasoning_tokens` (unchanged).
- Produces: `ContextBreakdown({ summary })` — same prop; renders one segmented gradient bar plus a color-keyed legend (replacing the old per-row bar list).

- [ ] **Step 1: Rewrite `ContextBreakdown.jsx`**

```jsx
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
```

- [ ] **Step 2: Remove only the now-fully-unused `.bar-row`/`.legend*` rules from `App.css`**

`ProjectList.jsx` still uses `.bar-track`/`.bar-fill` until Task 11 restyles it — leave those two classes in `App.css` for now. Delete only:
```css
.bar-row { display: grid; grid-template-columns: 110px 1fr 70px; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px; }
.legend { display: flex; gap: 16px; margin-top: 8px; font-size: 12px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-item i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
```

- [ ] **Step 3: Verify manually**

Run: `cd frontend && npm run dev`. Expected: below the hero total-tokens number, one thin multi-color segmented bar renders (green/blue/purple/orange/yellow), with a legend below showing each category's percentage and raw token count.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ContextBreakdown.jsx frontend/src/App.css
git commit -m "style(dashboard): restyle ContextBreakdown as a segmented gradient bar with legend"
```

---

## Task 10: Frontend — restyle `Heatmap.jsx`, `TrendChart.jsx`, `SyncLogCard.jsx` (visual only)

**Files:**
- Modify: `frontend/src/components/Heatmap.jsx`
- Modify: `frontend/src/components/TrendChart.jsx`
- Modify: `frontend/src/components/SyncLogCard.jsx`
- Modify: `frontend/src/App.css` (remove `.card`, `.heatmap-*` rules — `.bar-track`/`.bar-fill` still stay for `ProjectList.jsx` until Task 11)

**Interfaces:**
- No prop or data changes to any of the three components — this task only changes `className` values and the heatmap cell color constant.

- [ ] **Step 1: Restyle `Heatmap.jsx`**

In `frontend/src/components/Heatmap.jsx`, replace the returned JSX's outer wrapper and cell classes:

```jsx
  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4 mb-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Activity (last {DAYS_BACK} days)</h4>
      <div className="flex flex-col gap-1 overflow-x-auto">
        <div className="grid grid-flow-col auto-cols-[10px] gap-[3px] h-3" aria-hidden="true">
          {monthLabels.map((label, i) => (
            <div key={i} className="text-[9px] opacity-60 whitespace-nowrap">
              {label || ""}
            </div>
          ))}
        </div>
        <div
          className="grid grid-flow-col grid-rows-7 auto-cols-[10px] gap-[3px]"
          role="group"
          aria-label={`Daily token activity for the last ${DAYS_BACK} days`}
        >
          {weeks.map((week) =>
            week.map((d) => {
              if (d.placeholder) {
                return <div key={d.date} className="w-[10px] h-[10px] rounded-sm" aria-hidden="true" />;
              }
              const intensity = max ? d.tokens / max : 0;
              const hasData = d.tokens > 0;
              const label = `${d.date}: ${d.tokens.toLocaleString()} tokens`;
              return (
                <div
                  key={d.date}
                  role="img"
                  aria-label={label}
                  title={label}
                  tabIndex={0}
                  className={
                    hasData
                      ? "w-[10px] h-[10px] rounded-sm bg-accent focus-visible:outline focus-visible:outline-2"
                      : "w-[10px] h-[10px] rounded-sm bg-border dark:bg-border-dark focus-visible:outline focus-visible:outline-2"
                  }
                  style={hasData ? { opacity: 0.25 + intensity * 0.75 } : undefined}
                />
              );
            })
          )}
        </div>
      </div>
      <div className="text-xs opacity-60 mt-2">Less → More</div>
    </div>
  );
```

(Only the `return` statement's JSX changes — leave `toISODate`, `buildWeeks`, `buildMonthLabels`, and the `useEffect`/`useState` logic above it untouched.)

- [ ] **Step 2: Restyle `TrendChart.jsx`**

In `frontend/src/components/TrendChart.jsx`, replace the returned JSX's outer wrapper and legend classes:

```jsx
  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4 mb-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Usage trend (last 30 days)</h4>
      <svg
        width={dates.length * (barWidth + gap)}
        height={chartHeight}
        role="group"
        aria-label="Usage trend, last 30 days, stacked by source"
      >
        {dates.map((date, i) => {
          let yOffset = chartHeight;
          return sources.map((source, si) => {
            const tokens = byDate[date][source] || 0;
            const h = (tokens / maxTotal) * chartHeight;
            yOffset -= h;
            const label = `${date} — ${source}: ${tokens.toLocaleString()}`;
            return (
              <rect
                key={`${date}-${source}`}
                x={i * (barWidth + gap)}
                y={yOffset}
                width={barWidth}
                height={h}
                fill={COLORS[si % COLORS.length]}
                role="img"
                aria-label={label}
                tabIndex={0}
              >
                <title>{label}</title>
              </rect>
            );
          });
        })}
      </svg>
      <div className="flex flex-wrap gap-4 mt-2 text-xs">
        {sources.map((s, i) => (
          <span key={s} className="flex items-center gap-1">
            <i className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: COLORS[i % COLORS.length] }} />
            {s}: {((sourceTotals[s] / grandTotal) * 100).toFixed(1)}%
          </span>
        ))}
      </div>
    </div>
  );
```

(Leave the `dates`/`sources`/`byDate`/`sourceTotals`/`grandTotal`/`barWidth`/`gap`/`chartHeight` logic above it untouched.)

- [ ] **Step 3: Restyle `SyncLogCard.jsx`**

Replace `frontend/src/components/SyncLogCard.jsx` with:

```jsx
import { useEffect, useState } from "react";
import { getSyncStatus } from "../api.js";

export default function SyncLogCard({ refreshKey = 0 }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    getSyncStatus()
      .then(setStatus)
      .catch(() => setStatus({ last_collected_at: null, stores: [] }));
  }, [refreshKey]);

  if (status === null) {
    return (
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
        Loading sync status…
      </div>
    );
  }

  return (
    <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-4">
      <h4 className="text-xs uppercase tracking-wide opacity-60 mb-2">Sync log</h4>
      <p className="text-sm">Last collected: {status.last_collected_at || "Never"}</p>
      {status.stores.length === 0 ? (
        <p className="text-sm opacity-60">No remote stores configured.</p>
      ) : (
        <ul className="text-sm space-y-1 mt-2">
          {status.stores.map((s) => (
            <li key={s.name}>{s.name} — Last synced: {s.last_synced_at || "Never synced"}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Remove the now-unused `.heatmap-*` rules from `App.css`**

`ProjectList.jsx` and `ProjectsPage.jsx` still use `className="card"` until Task 11 restyles them — leave the `.card` rule in `App.css` for now (Task 12's final cleanup removes it once nothing references it). Delete only:

```css
.heatmap-wrapper { display: flex; flex-direction: column; gap: 4px; overflow-x: auto; }
.heatmap-months { display: grid; grid-auto-flow: column; grid-auto-columns: 10px; gap: 3px; height: 12px; }
.heatmap-month-label { font-size: 9px; opacity: 0.6; white-space: nowrap; }
.heatmap-grid { display: grid; grid-auto-flow: column; grid-template-rows: repeat(7, 10px); grid-auto-columns: 10px; gap: 3px; }
.heatmap-cell { width: 10px; height: 10px; border-radius: 2px; background: #3fb950; }
.heatmap-cell.empty { background: var(--border); opacity: 1; }
.heatmap-cell.has-data { background: #3fb950; }
.heatmap-cell.placeholder { background: transparent; }
.heatmap-cell:focus-visible { outline: 2px solid var(--text); outline-offset: 1px; }
.heatmap-legend { font-size: 11px; opacity: 0.6; margin-top: 8px; }
```

- [ ] **Step 5: Verify manually**

Run: `cd frontend && npm run dev`. Expected: heatmap, trend chart, and sync log all render inside dark-card-styled boxes matching the rest of the page; heatmap cells are green-tinted by intensity; hovering/tabbing to a cell still shows its tooltip/`aria-label`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Heatmap.jsx frontend/src/components/TrendChart.jsx frontend/src/components/SyncLogCard.jsx frontend/src/App.css
git commit -m "style(dashboard): restyle Heatmap, TrendChart, SyncLogCard cards with Tailwind"
```

---

## Task 11: Frontend — `HarnessSplit.jsx`, restyle `ProjectList.jsx`, restructure `ProjectsPage.jsx`

**Files:**
- Create: `frontend/src/components/HarnessSplit.jsx`
- Modify: `frontend/src/components/ProjectList.jsx`
- Modify: `frontend/src/pages/ProjectsPage.jsx`
- Modify: `frontend/src/App.css` (remove `.bar-track`/`.bar-fill`/`.project-list*` rules — now the last consumers are migrated)

**Interfaces:**
- Produces: `HarnessSplit({ summary })` — percentage-by-source list, styled like `ContextBreakdown`'s legend but keyed off `summary().harnesses` (same shape as `HarnessCards` consumes).
- `ProjectsPage.jsx` keeps its existing state/effects (`projects`, `selected`, `getProjectDetail`) — only the returned JSX and component composition change.

- [ ] **Step 1: Write `frontend/src/components/HarnessSplit.jsx`**

```jsx
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
```

- [ ] **Step 2: Restyle `ProjectList.jsx`, retitle to "Top projects"**

```jsx
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
```

- [ ] **Step 3: Restructure `ProjectsPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { getProjects, getProjectDetail } from "../api.js";
import ProjectList from "../components/ProjectList.jsx";
import HarnessSplit from "../components/HarnessSplit.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import { formatTokens } from "../format.js";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    getProjects({ period: "all" }).then((data) => {
      setProjects(data);
      if (!selected && data.length > 0) setSelected(data[0].project);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    getProjectDetail(selected, { period: "all" }).then(setDetail).catch(() => setDetail(null));
  }, [selected]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
      <ProjectList projects={projects} selected={selected} onSelect={setSelected} />
      <div className="bg-card dark:bg-card-dark border border-border dark:border-border-dark rounded-xl p-6">
        {selected ? (
          <>
            <h2 className="text-2xl font-semibold mb-1">{selected}</h2>
            <p className="text-3xl font-semibold mb-4">
              {detail ? formatTokens(detail.total_tokens).full : "—"}
            </p>
            <HarnessSplit summary={detail} />
            <ContextBreakdown summary={detail} />
          </>
        ) : (
          <p className="opacity-60">Select a project.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Remove the now-unused rules from `App.css`**

Delete these lines from `frontend/src/App.css`:
```css
.bar-track { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.bar-track.small { display: inline-block; width: 60px; margin-right: 6px; vertical-align: middle; }
.bar-fill { height: 100%; background: #5b8def; }
.project-list { list-style: none; padding: 0; margin: 0; }
.project-list li { padding: 8px; border-radius: 6px; cursor: pointer; display: grid; grid-template-columns: 1fr 100px 60px; gap: 8px; align-items: center; }
.project-list li.selected { background: var(--bg); font-weight: 600; }
```

- [ ] **Step 5: Verify manually**

Run: `cd frontend && npm run dev`, open the By Project page. Expected: left column shows "Top projects" with per-project token bars; clicking a project updates the right panel's title, total-tokens number, harness-split list, and context-breakdown bar; keyboard nav (Tab + Enter/Space) still selects a project.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/HarnessSplit.jsx frontend/src/components/ProjectList.jsx frontend/src/pages/ProjectsPage.jsx frontend/src/App.css
git commit -m "feat(dashboard): add HarnessSplit, restructure By Project page into list + detail panel"
```

---

## Task 12: Frontend — final `App.css` cleanup and full visual QA

**Files:**
- Modify: `frontend/src/App.css`

**Interfaces:** none — cleanup and verification only.

- [ ] **Step 1: Confirm no legacy rules remain**

Run: `cd frontend && grep -c "^\." src/App.css`
Expected: `0` — every hand-written class-selector rule was migrated and deleted across Tasks 4–11. `App.css` should now contain only the `@import "tailwindcss";` line, the `@custom-variant dark (...)` line, the `@theme { ... }` block, and the `body { margin: 0; font-family: system-ui, sans-serif; }` rule (the `background`/`color` properties on `body` are dropped in favor of the `bg-bg dark:bg-bg-dark text-fg dark:text-fg-dark` classes already applied to `App.jsx`'s root `div` in Task 6).

If any rule remains, delete it now (all consumers were migrated in Tasks 4–11) and re-run the grep to confirm `0`.

- [ ] **Step 2: Full visual QA against the mockup**

Run: `cd frontend && npm run dev`. With the dev server running:
1. Open the Tokens page in dark mode — compare layout, spacing, and colors against `docs/design/dashboard.html` (open it directly in a browser tab, e.g. `open docs/design/dashboard.html` from the repo root on macOS): sidebar branding, range tabs, stats/model-list card, sync log, hero total-tokens number, context-breakdown bar, harness cards, heatmap, trend chart.
2. Toggle to light mode — confirm every card/border/text color swaps correctly (no dark-only colors left over).
3. Open the By Project page in both themes — compare "Top projects" list and the selected-project detail panel (harness split + context breakdown) against the mockup's By Project screen.
4. Click through all four range tabs on the Tokens page and confirm the hero number, context breakdown, and harness cards update while the stats-row numbers (7d/30d/month/avg/Started/Active days) stay fixed.
5. Click several different projects on the By Project page and confirm the detail panel updates each time.

Fix any visual discrepancies found by adjusting Tailwind classes in the relevant component file(s) before proceeding.

- [ ] **Step 3: Run the full backend test suite**

Run: `python3 -m pytest -q`
Expected: all tests pass (no backend regressions from this redesign).

- [ ] **Step 4: Production build check**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors or warnings about missing Tailwind classes.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.css
git commit -m "chore(dashboard): remove legacy CSS after full Tailwind migration"
```
