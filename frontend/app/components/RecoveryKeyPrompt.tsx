"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function RecoveryKeyPrompt({ recoveryKey }: { recoveryKey: string }) {
  const [saved, setSaved] = useState(false);
  if (!recoveryKey) return null;
  return (
    <section className="rounded-lg border border-amber-300 bg-amber-50 p-4" aria-label="恢复密钥">
      <p className="font-medium">请立即离线保存恢复密钥</p>
      <p className="mt-1 text-xs text-muted-foreground">它只显示这一次；创建者 Cookie 过期或项目删除后需要它恢复。</p>
      <code className="mt-3 block break-all rounded bg-white p-2 text-xs">{recoveryKey}</code>
      <Button className="mt-3" size="sm" variant="outline" onClick={async () => { await navigator.clipboard.writeText(recoveryKey); setSaved(true); }}>
        {saved ? "已复制" : "复制恢复密钥"}
      </Button>
    </section>
  );
}
