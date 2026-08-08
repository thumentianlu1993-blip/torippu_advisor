"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ProjectForm from "./components/ProjectForm";
import RecoveryKeyPrompt from "./components/RecoveryKeyPrompt";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Calendar, Copy, Check, Compass, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function HomePage() {
  const router = useRouter();
  const [project, setProject] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState("");

  const handleCreated = (proj: any) => {
    setProject(proj);
    setCopied(false);
  };

  useEffect(() => {
    if (project) {
      setShareUrl(`${window.location.origin}/p/${project.share_token}`);
    }
  }, [project]);

  const copyToClipboard = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("分享链接已复制");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("复制失败");
    }
  };

  const viewReport = () => {
    if (!project) return;
    router.push(`/p/${project.share_token}`);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sand-100 via-background to-background px-4 py-8 sm:py-12 lg:py-16">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 text-center sm:mb-10">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-terracotta-50 px-3 py-1 text-xs font-medium text-terracotta-700 ring-1 ring-terracotta-200">
            <Compass className="size-3.5" />
            <span>从这里开启下一段旅程</span>
          </div>
          <h1 className="font-heading text-3xl font-bold text-foreground sm:text-4xl lg:text-5xl">
            旅行规划师
          </h1>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground sm:text-base">
            发现体验、对比选择，为下一次旅程生成可分享的旅行杂志。
          </p>
        </div>

        <ProjectForm onCreated={handleCreated} />

        {project && (
          <Card className="mt-6 animate-fade-in border-emerald-200 bg-emerald-50/60 editorial-shadow sm:mt-8">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="bg-emerald-100 text-emerald-800">
                  已创建
                </Badge>
                <CardTitle className="text-lg">行程方案已生成</CardTitle>
              </div>
              <CardDescription>
                把链接分享给同行伙伴，大家可以一起投票和补充。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <RecoveryKeyPrompt recoveryKey={project.recovery_key} />
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-4 text-terracotta-600" />
                  {project.destination}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Calendar className="size-4 text-terracotta-600" />
                  {project.duration_days} 天
                </span>
              </div>

              <div className="flex items-center gap-2 rounded-lg border bg-white/80 p-2">
                <input
                  readOnly
                  value={shareUrl}
                  className="min-w-0 flex-1 bg-transparent px-2 text-sm text-foreground outline-none"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={copyToClipboard}
                  className="shrink-0"
                >
                  {copied ? (
                    <>
                      <Check className="mr-1 size-4" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy className="mr-1 size-4" />
                      复制
                    </>
                  )}
                </Button>
              </div>

              <Button
                onClick={viewReport}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
              >
                查看报告
                <ArrowRight className="ml-1 size-4" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
