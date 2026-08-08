"use client";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function VoteVisibilityControl({ token, revealed, onChange }: { token: string; revealed: boolean; onChange: () => void }) {
  return (
    <section className="rounded-lg border p-4">
      <h3 className="font-medium">同行投票汇总</h3>
      <p className="mt-1 text-sm text-muted-foreground">当前{revealed ? "公开匿名汇总" : "隐藏汇总；访客只看自己的投票"}。</p>
      <Button className="mt-3" variant="outline" onClick={async () => { await api.setVotesVisibility(token, !revealed); onChange(); }}>{revealed ? "重新隐藏" : "公开汇总"}</Button>
    </section>
  );
}
