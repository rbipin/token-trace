// frontend/src/pages/ProjectsPage.jsx
import { useEffect, useState } from "react";
import { getProjects, getProjectDetail } from "../api.js";
import ProjectList from "../components/ProjectList.jsx";
import HarnessSplit from "../components/HarnessSplit.jsx";
import ContextBreakdown from "../components/ContextBreakdown.jsx";
import { formatTokens } from "../format.js";
import { useThemeCtx } from "../theme.js";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const { accent } = useThemeCtx();

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
    <div className="grid gap-5 items-start" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))" }}>
      <ProjectList projects={projects} selected={selected} onSelect={setSelected} />

      <div className="flex flex-col gap-5">
        <div className="border border-border dark:border-border-dark rounded-[14px] px-[26px] pt-[22px] pb-[26px] bg-card dark:bg-card-dark">
          {selected ? (
            <>
              <div className="text-[11px] font-semibold tracking-[0.14em] uppercase text-subtext dark:text-subtext-dark">
                Selected project
              </div>
              <div className="font-extrabold text-2xl font-mono mt-1.5">{selected}</div>
              <div className="flex items-baseline gap-3.5 flex-wrap mt-2.5">
                <span className="font-extrabold text-[clamp(30px,4vw,42px)] leading-[1.05] tracking-[-0.02em]">
                  {detail ? formatTokens(detail.total_tokens).full : "—"}
                </span>
                {detail && (
                  <span className="font-bold text-base" style={{ color: accent }}>
                    {formatTokens(detail.total_tokens).abbreviated}
                  </span>
                )}
              </div>
              <HarnessSplit summary={detail} />
            </>
          ) : (
            <p className="text-subtext dark:text-subtext-dark">Select a project.</p>
          )}
        </div>
        {selected && <ContextBreakdown summary={detail} />}
      </div>
    </div>
  );
}
