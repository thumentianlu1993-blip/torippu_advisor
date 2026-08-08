"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProjectRecovery({ token }: { token: string }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  return (
    <div className="mt-5 w-full border-t pt-4">
      <p className="text-sm font-medium">使用离线恢复密钥</p>
      <Input className="mt-2" type="password" value={key} onChange={(event) => setKey(event.target.value)} aria-label="恢复密钥" />
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
      <Button className="mt-2" variant="outline" disabled={!key} onClick={async () => { try { const result = await api.recoverProject(token, key); window.location.replace(`/p/${result.share_token}`); } catch { setError("恢复失败或恢复窗口已过期"); } }}>恢复创建者权限</Button>
    </div>
  );
}
