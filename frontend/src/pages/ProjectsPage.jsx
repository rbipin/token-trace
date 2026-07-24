// frontend/src/pages/ProjectsPage.jsx
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
