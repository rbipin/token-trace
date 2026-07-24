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
