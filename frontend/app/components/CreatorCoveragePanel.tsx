"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function CreatorCoveragePanel({ token }: { token: string }) {
  const [data, setData] = useState<any | null>(null);
  useEffect(() => { api.getCreatorCoverage(token).then(setData).catch(() => setData(null)); }, [token]);
  if (!data) return null;
  return (
    <section className="rounded-lg border p-4 md:col-span-2">
      <h3 className="font-medium">采集覆盖与预算</h3>
      <p className="mt-1 text-sm">外部请求 {data.request_units ?? 0}/{data.request_limit ?? 500}；估算付费 ${Number(data.estimated_cost_usd ?? 0).toFixed(3)}/${data.cost_limit_usd ?? 2}</p>
      {data.blocked_reason && <p className="mt-1 text-sm text-destructive">已停止新的外部采集，请使用现有数据、缓存或手工地点。</p>}
      <ul className="mt-2 text-xs text-muted-foreground">
        {Object.entries(data.source_statuses || {}).map(([source, ok]) => <li key={source}>{source}: {ok ? "可用" : "当前不完整"}</li>)}
      </ul>
    </section>
  );
}
