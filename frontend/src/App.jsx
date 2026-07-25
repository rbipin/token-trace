import { useEffect, useState } from "react";
import TokensPage from "./pages/TokensPage.jsx";
import ProjectsPage from "./pages/ProjectsPage.jsx";
import { ACCENT, ThemeContext } from "./theme.js";
import "./App.css";

const NAV_ITEMS = [
  { key: "tokens", icon: "▤", label: "Tokens" },
  { key: "limits", icon: "◔", label: "Limits", disabled: true },
  { key: "projects", icon: "▣", label: "By Project" },
];

export default function App() {
  const [page, setPage] = useState("tokens");
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ dark: theme === "dark", accent: ACCENT }}>
    <div className="flex min-h-screen bg-bg dark:bg-bg-dark text-fg dark:text-fg-dark font-sans transition-colors">
      <aside className="w-[250px] shrink-0 px-4 py-[22px] flex flex-col gap-[26px] border-r border-border dark:border-border-dark">
        <div className="flex items-center gap-2.5 px-1.5">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center font-mono font-extrabold text-sm text-bg dark:text-bg-dark">
            T
          </div>
          <span className="font-bold text-[15px] tracking-tight">Token Trace</span>
        </div>

        <div className="flex flex-col gap-0.5">
          <div className="text-[10.5px] font-semibold tracking-[0.12em] uppercase text-subtext dark:text-subtext-dark px-2.5 mb-1.5">
            General
          </div>
          {NAV_ITEMS.map((item) => {
            const active = page === item.key;
            return (
              <button
                key={item.key}
                disabled={item.disabled}
                onClick={() => !item.disabled && setPage(item.key)}
                className={
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13.5px] font-medium text-left tt-tab" +
                  (active
                    ? " bg-pill dark:bg-pill-dark text-fg dark:text-fg-dark"
                    : item.disabled
                      ? " text-subtext dark:text-subtext-dark opacity-50 cursor-default"
                      : " text-subtext dark:text-subtext-dark hover:text-fg dark:hover:text-fg-dark")
                }
              >
                <span className="text-sm w-4 text-center">{item.icon}</span>
                {item.label}
              </button>
            );
          })}
        </div>

        <button
          className="mt-auto flex items-center gap-2 text-xs font-medium text-subtext dark:text-subtext-dark tt-tab"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <span className="w-2 h-2 rounded-full bg-accent" />
          {theme === "dark" ? "Dark mode" : "Light mode"}
        </button>
      </aside>

      <main className="flex-1 min-w-0 px-7 pt-[26px] pb-[60px]">
        {page === "tokens" ? <TokensPage /> : <ProjectsPage />}
      </main>
    </div>
    </ThemeContext.Provider>
  );
}
