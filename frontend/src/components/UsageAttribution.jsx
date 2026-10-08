export default function UsageAttribution({ attribution }) {
  if (!attribution) return null;
  return (
    <div className="text-xs text-subtext dark:text-subtext-dark mt-3 space-y-1">
      {attribution.legacy_tokens > 0 && <p>Some historical usage is assigned to session start dates.</p>}
      {attribution.partial_session_count > 0 && <p>{attribution.partial_session_count} session(s) have partial usage; totals include only recorded consumption.</p>}
      {attribution.unavailable_session_count > 0 && <p>{attribution.unavailable_session_count} session(s) have usage unavailable; consumption is unknown.</p>}
    </div>
  );
}
