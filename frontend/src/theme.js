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
const HARNESS_TABLE = {
  Claude: { icon: "✳", color: (dark) => (dark ? "#22c55e" : "#22c55e") },
  Codex: { icon: "◐", color: (dark) => (dark ? "#3b82f6" : "#2563eb") },
  Cursor: { icon: "◈", color: (dark) => (dark ? "#a78bfa" : "#7c3aed") },
  OpenCode: { icon: "◻", color: (dark, subtext) => subtext },
  Antigravity: { icon: "▲", color: (dark, subtext) => subtext },
  "Kilo-CLI": { icon: "◆", color: (dark, subtext) => subtext },
  CodeBuddy: { icon: "◎", color: (dark, subtext) => subtext },
  Copilot: { icon: "⌘", color: (dark) => (dark ? "#f472b6" : "#db2777") },
};

export function harnessIcon(name) {
  return HARNESS_TABLE[name]?.icon ?? "•";
}

export function harnessColor(name, dark, subtext, accent) {
  const entry = HARNESS_TABLE[name];
  if (!entry) return subtext;
  if (name === "Claude") return accent;
  return entry.color(dark, subtext);
}
