"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api, type Project, type Report, type Candidate } from "@/lib/api";
import ReportNav from "@/app/components/ReportNav";
import CoreExperiencesSection from "@/app/components/report/CoreExperiencesSection";
import ImportantExperiencesSection from "@/app/components/report/ImportantExperiencesSection";
import FoodSection from "@/app/components/report/FoodSection";
import LodgingSection from "@/app/components/report/LodgingSection";
import TransportSection from "@/app/components/report/TransportSection";
import BudgetSection from "@/app/components/report/BudgetSection";
import TipsSection from "@/app/components/report/TipsSection";
import ReferenceRoutesSection from "@/app/components/report/ReferenceRoutesSection";
import ReportSkeleton from "@/app/components/report/ReportSkeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "sonner";
import {
  MapPin,
  Calendar,
  Users,
  RefreshCw,
  Download,
  AlertCircle,
  Compass,
} from "lucide-react";

const SECTIONS = [
  { key: "core_experiences", label: "核心" },
  { key: "important_experiences", label: "重要" },
  { key: "food", label: "美食" },
  { key: "lodging", label: "住宿" },
  { key: "transport", label: "交通" },
  { key: "budget", label: "预算" },
  { key: "tips", label: "贴士" },
  { key: "reference_routes", label: "路线" },
];

function statusBadgeVariant(status?: string): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "success":
      return "default";
    case "collecting":
    case "processing":
      return "secondary";
    case "failed":
      return "destructive";
    default:
      return "outline";
  }
}

function ProjectHeader({
  project,
  status,
  report,
  isCreator,
  onRecollect,
  onExport,
  recollecting,
}: {
  project: Project;
  status: any;
  report: Report | null;
  isCreator: boolean;
  onRecollect: () => void;
  onExport: () => void;
  recollecting: boolean;
}) {
  return (
    <Card className="overflow-hidden editorial-shadow">
      <CardContent className="p-0">
        <div className="bg-gradient-to-br from-terracotta-600 to-terracotta-800 px-5 py-6 text-white sm:px-8 sm:py-8">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="secondary"
              className="bg-white/15 text-white hover:bg-white/20"
            >
              {status?.status === "success"
                ? "已完成"
                : status?.status === "collecting"
                ? "采集中"
                : status?.status === "ready"
                ? "已就绪"
                : status?.status || "加载中"}
            </Badge>
            {report && (
              <Badge
                variant="secondary"
                className="bg-white/15 text-white hover:bg-white/20"
              >
                报告 {report.progress}%
              </Badge>
            )}
          </div>
          <h1 className="mt-3 font-heading text-2xl font-bold sm:text-3xl lg:text-4xl">
            {project.destination}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-white/90">
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="size-4" /> {project.duration_days} 天
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="size-4" /> 从 {project.departure} 出发
            </span>
            {project.traveler_structure && (
              <span className="inline-flex items-center gap-1.5">
                <Users className="size-4" /> {project.traveler_structure}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 border-t bg-muted/30 px-5 py-3 sm:px-8">
          {isCreator && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRecollect}
              disabled={recollecting}
              className="text-xs"
            >
              <RefreshCw className={`mr-1 size-3.5 ${recollecting ? "animate-spin" : ""}`} />
              {recollecting ? "正在重新采集…" : "重新采集"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onExport} className="text-xs">
            <Download className="mr-1 size-3.5" /> 导出 Google Maps
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ReportPage() {
  const rawToken = useParams().token;
  const token = Array.isArray(rawToken) ? rawToken[0] : rawToken;
  const searchParams = useSearchParams();
  const creatorToken = searchParams.get("creator_token");
  const [isCreator, setIsCreator] = useState(false);

  const [project, setProject] = useState<Project | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [status, setStatus] = useState<any | null>(null);
  const [activeSection, setActiveSection] = useState("core_experiences");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recollecting, setRecollecting] = useState(false);

  const loadData = useCallback(async () => {
    if (!token || Array.isArray(token)) return;
    try {
      const proj = await api.getProjectByToken(token);
      setProject(proj);
      // Creator status is validated server-side; the public project
      // response intentionally no longer carries the creator token.
      if (creatorToken) {
        try {
          const check = await api.creatorCheck(token, creatorToken);
          setIsCreator(!!check.creator);
        } catch {
          setIsCreator(false);
        }
      } else {
        setIsCreator(false);
      }
      const [rep, cands, stat] = await Promise.all([
        api.getReport(token),
        api.getCandidates(token),
        api.getProjectStatus(token),
      ]);
      setReport(rep);
      setCandidates(cands);
      setStatus(stat);
      setError("");
    } catch (err: any) {
      setError(err.message || "加载报告失败");
    } finally {
      setLoading(false);
    }
  }, [token, creatorToken]);

  useEffect(() => {
    if (!token || Array.isArray(token)) return;
    loadData();
  }, [token, loadData]);

  // SSE stream for report progress
  useEffect(() => {
    if (!project) return;
    if (report?.status === "success") return;

    let es: EventSource | null = null;
    try {
      es = api.streamReport(project.id);
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.status || data.progress !== undefined) {
            setReport((prev) => (prev ? { ...prev, ...data } : { status: data.status, progress: data.progress || 0, content: data.content || {} }));
          }
          if (data.status === "success" || data.status === "failed") {
            loadData();
          }
        } catch {
          // ignore non-JSON messages
        }
      };
      es.onerror = () => {
        // SSE will retry automatically; if it fails permanently we fall back to silent
      };
    } catch {
      // EventSource not available or failed; ignore
    }
    return () => {
      if (es) es.close();
    };
  }, [project, report?.status, loadData]);

  const handleExport = async () => {
    if (!token || Array.isArray(token)) return;
    try {
      const data = await api.exportGoogleMaps(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.destination?.replace(/\s+/g, "_") || "trip"}_google_maps.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("已导出 Google Maps");
    } catch (err: any) {
      toast.error(err.message || "导出失败");
    }
  };

  const handleRecollect = async () => {
    if (!token || Array.isArray(token)) return;
    setRecollecting(true);
    try {
      await api.recollect(token, creatorToken || "");
      setStatus((prev: any) => ({ ...prev, status: "collecting" }));
      toast.success("已开始重新采集");
      loadData();
    } catch (err: any) {
      toast.error(err.message || "重新采集失败");
    } finally {
      setRecollecting(false);
    }
  };

  if (loading) return <ReportSkeleton />;
  if (error)
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <Card className="max-w-md">
          <CardContent className="flex flex-col items-center py-10 text-center">
            <AlertCircle className="mb-3 size-10 text-destructive" />
            <h2 className="font-heading text-lg font-semibold">无法加载报告</h2>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            <Button onClick={loadData} className="mt-4">重试</Button>
          </CardContent>
        </Card>
      </div>
    );
  if (!project || !report) return <ReportSkeleton />;

  const content = report.content || {};

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 pb-12 sm:px-8">
        <div className="py-6 sm:py-8">
          <ProjectHeader
            project={project}
            status={status}
            report={report}
            isCreator={isCreator}
            onRecollect={handleRecollect}
            onExport={handleExport}
            recollecting={recollecting}
          />
        </div>

        <ReportNav active={activeSection} onSelect={setActiveSection} />

        <section className="mt-6 min-h-[50vh]">
          {activeSection === "core_experiences" && <CoreExperiencesSection content={content} />}
          {activeSection === "important_experiences" && (
            <ImportantExperiencesSection
              candidates={candidates}
              projectId={project.id}
              isCreator={isCreator}
              creatorToken={creatorToken}
              votesRevealed={project.votes_revealed}
              onChange={loadData}
            />
          )}
          {activeSection === "food" && <FoodSection content={content} />}
          {activeSection === "lodging" && <LodgingSection content={content} />}
          {activeSection === "transport" && <TransportSection content={content} />}
          {activeSection === "budget" && <BudgetSection content={content} />}
          {activeSection === "tips" && <TipsSection content={content} />}
          {activeSection === "reference_routes" && <ReferenceRoutesSection content={content} />}
        </section>

        {content.source_disclaimer && (
          <p className="mt-10 text-center text-xs text-muted-foreground">{content.source_disclaimer}</p>
        )}
      </div>
    </main>
  );
}
