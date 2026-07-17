"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import CandidateList from "@/app/components/CandidateList";
import ReportNav from "@/app/components/ReportNav";

export default function ReportPage() {
  const { token } = useParams();
  const [project, setProject] = useState<any | null>(null);
  const [report, setReport] = useState<any | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [status, setStatus] = useState<any | null>(null);
  const [activeSection, setActiveSection] = useState("core_experiences");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isCreator] = useState(true); // MVP: treat viewer as creator for editing.

  const loadData = async () => {
    try {
      const proj = await api.getProjectByToken(token as string);
      setProject(proj);
      const [rep, cands, stat] = await Promise.all([
        api.getReport(proj.id),
        api.getCandidates(proj.id),
        api.getProjectStatus(proj.id),
      ]);
      setReport(rep);
      setCandidates(cands);
      setStatus(stat);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to load report");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    loadData();
    const interval = setInterval(() => {
      if (status && status.report_status !== "success") {
        loadData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [token, status?.report_status]);

  const handleExport = async () => {
    if (!project) return;
    const data = await api.exportGoogleMaps(project.id);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${project.destination.replace(/\s+/g, "_")}_google_maps.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRecollect = async () => {
    if (!project) return;
    await api.recollect(project.id);
    setStatus({ ...status, status: "collecting" });
    loadData();
  };

  if (loading) return <div className="p-8 text-center">Loading...</div>;
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!project || !report) return <div className="p-8 text-center">Not found</div>;

  const content = report.content || {};
  const votesRevealed = project.votes_revealed;

  return (
    <main className="min-h-screen p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <header className="mb-6">
          <h1 className="text-2xl md:text-3xl font-bold">{project.destination}</h1>
          <p className="text-gray-600">
            {project.duration_days} days · {project.departure} · Status: {status?.status}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {isCreator && (
              <button
                onClick={handleRecollect}
                className="px-4 py-2 bg-blue-600 text-white rounded text-sm"
              >
                Re-collect
              </button>
            )}
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm"
            >
              Export to Google Maps
            </button>
            <span className="text-sm px-3 py-2 bg-gray-100 rounded">
              Report: {report.status} ({report.progress}%)
            </span>
          </div>
        </header>

        <ReportNav active={activeSection} onSelect={setActiveSection} />

        <section className="mb-8">
          {activeSection === "core_experiences" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Core Experiences</h2>
              {content.core_experiences?.length ? (
                <ul className="list-disc pl-5 space-y-1">
                  {content.core_experiences.map((item: any, i: number) => (
                    <li key={i}>{item.name} — {item.reason}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500">No core experiences yet. Wait for collection or add manually.</p>
              )}
            </div>
          )}

          {activeSection === "important_experiences" && (
            <CandidateList
              candidates={candidates}
              projectId={project.id}
              isCreator={isCreator}
              votesRevealed={votesRevealed}
              onChange={loadData}
            />
          )}

          {activeSection === "food" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Food</h2>
              <h3 className="font-medium">Reservation Pool</h3>
              <p className="text-gray-600">{JSON.stringify(content.food?.reservation_pool)}</p>
              <h3 className="font-medium mt-4">Random Pool</h3>
              <p className="text-gray-600">{JSON.stringify(content.food?.random_pool)}</p>
            </div>
          )}

          {activeSection === "lodging" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Lodging</h2>
              <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(content.lodging, null, 2)}</pre>
            </div>
          )}

          {activeSection === "transport" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Transport</h2>
              <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(content.transport, null, 2)}</pre>
            </div>
          )}

          {activeSection === "budget" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Budget</h2>
              <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(content.budget, null, 2)}</pre>
            </div>
          )}

          {activeSection === "tips" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Tips</h2>
              <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(content.tips, null, 2)}</pre>
            </div>
          )}

          {activeSection === "reference_routes" && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Reference Routes</h2>
              <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(content.reference_routes, null, 2)}</pre>
            </div>
          )}
        </section>

        <p className="text-xs text-gray-500 mt-8">{content.source_disclaimer}</p>
      </div>
    </main>
  );
}
