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
