import { createContext, useContext } from "react";

export const ACCENT = "#22c55e";

export const ThemeContext = createContext({ dark: true, accent: ACCENT });

export function useThemeCtx() {
  return useContext(ThemeContext);
}

export function hexRgb(hex) {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

export function rgba(hex, a) {
  const [r, g, b] = hexRgb(hex);
  return `rgba(${r},${g},${b},${a.toFixed(3)})`;
}

// Harness icon + brand accent, matched per-theme (dark/light variant of each hue).
// Keyed by the raw `source` string collectors write to SessionRecord (see collectors/*.py).
const HARNESS_TABLE = {
  claude_cli: { label: "Claude", icon: "✳", color: (dark) => (dark ? "#22c55e" : "#22c55e") },
  copilot_cli: { label: "Copilot", icon: "⌘", color: (dark) => (dark ? "#f472b6" : "#db2777") },
};

export function harnessLabel(source) {
  return HARNESS_TABLE[source]?.label ?? source;
}

export function harnessIcon(source) {
  return HARNESS_TABLE[source]?.icon ?? "•";
}

export function harnessColor(source, dark, subtext, accent) {
  const entry = HARNESS_TABLE[source];
  if (!entry) return subtext;
  if (source === "claude_cli") return accent;
  return entry.color(dark, subtext);
}
