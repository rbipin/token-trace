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
