import { useEffect, useState } from "react";
import { getSyncStatus } from "../api.js";
import { formatRelativeTime } from "../relativeTime.js";
import { useThemeCtx } from "../theme.js";

function formatBig(iso) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function SyncLogCard({ refreshKey = 0 }) {
  const [status, setStatus] = useState(null);
  const { accent } = useThemeCtx();

  useEffect(() => {
    getSyncStatus()
      .then(setStatus)
      .catch(() => setStatus({ last_collected_at: null, stores: [] }));
  }, [refreshKey]);

  if (status === null) {
    return (
      <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark text-subtext dark:text-subtext-dark text-sm">
        Loading sync status…
      </div>
    );
  }

  const lastSync =
    status.stores.reduce((latest, s) => {
      if (!s.last_synced_at) return latest;
      return !latest || s.last_synced_at > latest ? s.last_synced_at : latest;
    }, null) || status.last_collected_at;

  return (
    <div className="border border-border dark:border-border-dark rounded-[14px] p-5 bg-card dark:bg-card-dark">
      <div className="flex items-center justify-between">
        <span className="font-bold text-xs tracking-[0.08em] uppercase">Sync log</span>
        <span className="flex items-center gap-1.5 font-semibold text-[11.5px]" style={{ color: accent }}>
          <span className="w-[7px] h-[7px] rounded-full" style={{ background: accent }} />
          {status.stores.length === 0 ? "Local only" : "Up to date"}
        </span>
      </div>
      <div className="text-xs text-subtext dark:text-subtext-dark mt-1.5">
        Local database ↔ remote server
      </div>
      <div className="font-bold text-[22px] mt-3">{formatBig(lastSync)}</div>
      <div className="font-mono text-xs text-subtext dark:text-subtext-dark mt-1">
        {lastSync ? formatRelativeTime(lastSync) : "Never synced"}
      </div>
      {status.stores.length > 0 && (
        <ul className="text-xs text-subtext dark:text-subtext-dark space-y-1 mt-3 pt-3 border-t border-border dark:border-border-dark">
          {status.stores.map((s) => (
            <li key={s.name}>
              {s.name} — {s.last_synced_at ? formatRelativeTime(s.last_synced_at) : "Never synced"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
