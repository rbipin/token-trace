async function getJSON(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null),
  ).toString();
  const url = query ? `${path}?${query}` : path;
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || `request failed: ${res.status}`);
  }
  return res.json();
}

export const getSummary = (params) => getJSON("/api/summary", params);
export const getHeatmap = (days) => getJSON("/api/heatmap", { days });
export const getTrend = (days) => getJSON("/api/trend", { days });
export const getProjects = (params) => getJSON("/api/projects", params);
export const getProjectDetail = (project, params) =>
  getJSON("/api/projects/detail", { ...params, project });
// SQLite's datetime('now') stores UTC without a timezone marker (e.g. "2026-07-25 04:34:56"),
// which `new Date(...)` would otherwise misparse as local time.
function asUtcIso(sqliteTimestamp) {
  if (!sqliteTimestamp) return sqliteTimestamp;
  return sqliteTimestamp.includes("T")
    ? sqliteTimestamp
    : `${sqliteTimestamp.replace(" ", "T")}Z`;
}

export const getSyncStatus = () =>
  getJSON("/api/sync-status").then((status) => ({
    ...status,
    last_collected_at: asUtcIso(status.last_collected_at),
    stores: status.stores.map((s) => ({
      ...s,
      last_synced_at: asUtcIso(s.last_synced_at),
    })),
  }));
export const getMeta = () => getJSON("/api/meta");
