"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const initial = { name: "", category: "niche", area: "", source_url: "", notes: "", tier: "optional", summary: "" };

export default function ManualCandidateEditor({ token, onChange }: { token: string; onChange: () => void }) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const field = (name: keyof typeof initial, placeholder: string) => <Input aria-label={placeholder} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} placeholder={placeholder} />;
  return (
    <section className="rounded-lg border p-4">
      <h3 className="font-medium">手工添加地点</h3>
      <div className="mt-3 grid gap-2">
        {field("name", "地点名称（必填）")}
        {field("category", "地点类别（必填）")}
        {field("area", "区域（可选）")}
        {field("source_url", "来源链接（可选）")}
        {field("tier", "建议档位（可选）")}
        <Textarea aria-label="备注（可选）" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="备注（可选）" />
        <Button disabled={!form.name.trim() || !form.category.trim() || busy} onClick={async () => { setBusy(true); try { await api.addCandidate(token, form); setForm(initial); onChange(); } finally { setBusy(false); } }}>添加</Button>
      </div>
    </section>
  );
}
