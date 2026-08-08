"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function MergeReviewQueue({ token }: { token: string }) {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api.getMergeProposals(token).then(setItems).catch(() => setItems([])); }, [token]);
  return (
    <section className="rounded-lg border p-4 md:col-span-2">
      <h3 className="font-medium">疑似重复审核</h3>
      {items.length === 0 ? <p className="mt-1 text-sm text-muted-foreground">暂无需要审核的地点。</p> : items.map((item) => (
        <div key={item.id} className="mt-3 flex items-center justify-between gap-2">
          <span>{item.name_a} / {item.name_b}</span>
          <div className="flex gap-2"><Button size="sm" onClick={() => api.decideMerge(token, item.id, "merge")}>合并</Button><Button size="sm" variant="outline" onClick={() => api.decideMerge(token, item.id, "keep_separate")}>保持分开</Button></div>
        </div>
      ))}
    </section>
  );
}
