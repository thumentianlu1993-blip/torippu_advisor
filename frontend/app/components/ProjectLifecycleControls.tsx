"use client";

import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function ProjectLifecycleControls({ token }: { token: string }) {
  const router = useRouter();
  return (
    <section className="rounded-lg border p-4 md:col-span-2">
      <h3 className="font-medium">分享与项目管理</h3>
      <p className="mt-1 text-sm text-muted-foreground">轮换后旧分享链接立即失效；删除后有 30 天恢复窗口。</p>
      <div className="mt-3 flex gap-2">
        <Button variant="outline" onClick={async () => { const result = await api.rotateShare(token); router.replace(`/p/${result.share_token}`); }}>轮换分享链接</Button>
        <Button variant="destructive" onClick={async () => { if (confirm("删除后链接立即失效。继续？")) { await api.deleteProject(token); router.refresh(); } }}>删除项目</Button>
      </div>
    </section>
  );
}
