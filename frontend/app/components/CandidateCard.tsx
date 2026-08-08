"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import Image from "next/image";
import {
  ThumbsUp,
  ThumbsDown,
  Minus,
  MapPin,
  Clock,
  ChevronDown,
  ChevronUp,
  Star,
  Trash2,
  MessageSquareText,
  ExternalLink,
  Pencil,
  History,
} from "lucide-react";
import { toast } from "sonner";

const TIERS = [
  { value: "must_go", label: "必去" },
  { value: "strongly_recommended", label: "强烈推荐" },
  { value: "optional", label: "可选" },
  { value: "resource_pool", label: "备选池" },
  { value: "discarded", label: "排除" },
];

const VOTE_TYPES = [
  { key: "like", label: "想去", icon: ThumbsUp },
  { key: "dislike", label: "不想去", icon: ThumbsDown },
  { key: "neutral", label: "中立", icon: Minus },
];

function ReviewSheet({ snippets }: { snippets: any[] }) {
  const [open, setOpen] = useState(false);
  if (!snippets?.length) return null;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-primary">
            <MessageSquareText className="mr-1 size-3.5" />
            查看评价
          </Button>
        }
      />
      <SheetContent side="bottom" className="h-[80vh] rounded-t-2xl">
        <SheetHeader>
          <SheetTitle>热门攻略与评价</SheetTitle>
          <SheetDescription>来自小红书、大众点评、TripAdvisor 等平台的真实分享</SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-4 overflow-auto pb-6">
          {snippets.map((snippet: any, i: number) => (
            <Card key={i} className="border border-border/60">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {snippet.source || "攻略"}
                  </Badge>
                  {snippet.url && (
                    <a
                      href={snippet.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-0.5 text-xs text-primary hover:underline"
                    >
                      原文 <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
                {snippet.rating && (
                  <p className="mt-2 text-xs text-amber-600">{"⭐".repeat(Math.min(Number(snippet.rating), 5))}</p>
                )}
                <p className="mt-2 text-sm leading-relaxed text-foreground">{snippet.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default function CandidateCard({
  candidate,
  token,
  isCreator,
  votesRevealed,
  onChange,
}: {
  candidate: any;
  token: string;
  isCreator: boolean;
  votesRevealed: boolean;
  onChange: () => void;
}) {
  const [userVote, setUserVote] = useState(candidate.user_vote || null);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [edit, setEdit] = useState({
    name: candidate.name || "",
    category: candidate.category || "",
    area: candidate.area || "",
    source_url: candidate.source_url || "",
    notes: candidate.notes || "",
    tier: candidate.tier || "optional",
    summary: candidate.summary || "",
  });

  const handleVote = async (voteType: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await api.vote(token, candidate.id, voteType);
      setUserVote(voteType);
      onChange();
      toast.success("投票已保存");
    } catch (err: any) {
      toast.error(err.message || "投票失败");
    } finally {
      setBusy(false);
    }
  };

  const handleTierChange = async (value: string | null) => {
    if (busy || !value) return;
    setBusy(true);
    try {
      await api.updateCandidate(token, candidate.id, { tier: value });
      onChange();
      toast.success("等级已更新");
    } catch (err: any) {
      toast.error(err.message || "更新失败");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("确定删除这个候选？")) return;
    try {
      await api.deleteCandidate(token, candidate.id);
      onChange();
      toast.success("已删除");
    } catch (err: any) {
      toast.error(err.message || "删除失败");
    }
  };

  const saveOverrides = async () => {
    setBusy(true);
    try {
      await api.updateCandidate(token, candidate.id, { ...edit, version: candidate.version });
      setEditing(false);
      onChange();
      toast.success("人工覆盖已保存");
    } catch (err: any) {
      toast.error(err.message || "保存失败");
    } finally {
      setBusy(false);
    }
  };

  const loadHistory = async () => {
    try {
      setHistory(await api.getCandidateHistory(token, candidate.id));
    } catch (err: any) {
      toast.error(err.message || "读取历史失败");
    }
  };

  const hasLongSummary = candidate.summary && candidate.summary.length > 120;
  const displaySummary =
    expanded || !hasLongSummary
      ? candidate.summary
      : `${candidate.summary.slice(0, 120)}…`;

  const rating = candidate.rating ?? candidate.google_rating;
  const pros = candidate.pros || [];
  const cons = candidate.cons || [];
  const snippets = candidate.review_snippets || [];

  return (
    <Card className="overflow-hidden editorial-shadow">
      <CardContent className="p-0">
        <div className="flex flex-col sm:flex-row">
          {/* Thumbnail */}
          <div className="relative h-40 w-full shrink-0 bg-muted sm:h-auto sm:w-40">
            {candidate.image_url || candidate.photos?.[0] ? (
              <Image
                src={candidate.image_url || candidate.photos[0]}
                alt={candidate.name}
                fill
                unoptimized
                className="object-cover"
                sizes="(max-width: 640px) 100vw, 160px"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-sand-100 to-sand-200">
                <MapPin className="size-8 text-sand-400" />
              </div>
            )}
            {candidate.price_level !== undefined && candidate.price_level !== null && (
              <div className="absolute left-2 top-2 rounded-md bg-black/60 px-2 py-0.5 text-xs font-medium text-white">
                {"$".repeat(Number(candidate.price_level) + 1)}
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex flex-1 flex-col p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-heading text-lg font-semibold leading-tight">{candidate.name}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  {candidate.area && (
                    <span className="inline-flex items-center gap-0.5">
                      <MapPin className="size-3" /> {candidate.area}
                    </span>
                  )}
                  {candidate.category && (
                    <Badge variant="secondary" className="text-xs">
                      {candidate.category}
                    </Badge>
                  )}
                  {rating !== undefined && rating !== null && (
                    <span className="inline-flex items-center gap-0.5 text-amber-600">
                      <Star className="size-3 fill-current" /> {Number(rating).toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
              {isCreator && (
                <Button
                  variant="ghost"
                  size="icon-xs"
                  onClick={handleDelete}
                  aria-label="删除候选"
                  className="shrink-0 text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="size-4" />
                </Button>
              )}
            </div>

            {displaySummary && (
              <div className="mt-3">
                <p className="text-sm leading-relaxed text-muted-foreground">{displaySummary}</p>
                {hasLongSummary && (
                  <button
                    type="button"
                    onClick={() => setExpanded((v) => !v)}
                    className="mt-1 inline-flex items-center gap-0.5 text-xs font-medium text-primary hover:underline"
                  >
                    {expanded ? (
                      <>收起 <ChevronUp className="size-3" /></>
                    ) : (
                      <>展开 <ChevronDown className="size-3" /></>
                    )}
                  </button>
                )}
              </div>
            )}

            {/* Pros / Cons */}
            {(pros.length > 0 || cons.length > 0) && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {pros.slice(0, 3).map((p: string) => (
                  <Badge key={p} variant="secondary" className="bg-emerald-50 text-emerald-700 text-xs">
                    ✓ {p}
                  </Badge>
                ))}
                {cons.slice(0, 2).map((c: string) => (
                  <Badge key={c} variant="outline" className="border-terracotta-200 text-terracotta-700 text-xs">
                    ✗ {c}
                  </Badge>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-3">
              {candidate.opening_hours && (
                <p className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="size-3" /> {candidate.opening_hours}
                </p>
              )}
              <ReviewSheet snippets={snippets} />
            </div>

            {isCreator && (
              <div className="mt-3 rounded-lg border bg-muted/20 p-3">
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEditing((value) => !value)}>
                    <Pencil className="mr-1 size-3.5" /> 编辑人工覆盖
                  </Button>
                  <Button size="sm" variant="ghost" onClick={loadHistory}>
                    <History className="mr-1 size-3.5" /> 字段历史
                  </Button>
                </div>
                {editing && (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {(["name", "category", "area", "source_url", "notes", "tier"] as const).map((field) => (
                      <Input key={field} aria-label={`编辑 ${field}`} value={edit[field]} onChange={(event) => setEdit({ ...edit, [field]: event.target.value })} placeholder={field} />
                    ))}
                    <Textarea className="sm:col-span-2" aria-label="编辑 summary" value={edit.summary} onChange={(event) => setEdit({ ...edit, summary: event.target.value })} placeholder="summary" />
                    <div className="sm:col-span-2"><Button size="sm" disabled={busy} onClick={saveOverrides}>保存</Button></div>
                  </div>
                )}
                {history.length > 0 && (
                  <div className="mt-3 space-y-2 text-xs">
                    {history.slice(0, 10).map((item) => (
                      <div key={item.id} className="flex items-center justify-between gap-2 rounded border bg-background p-2">
                        <span>{item.field_name}: {String(item.old_value ?? "（系统值）")} → {String(item.new_value ?? "（空）")}</span>
                        <Button size="xs" variant="ghost" onClick={async () => { await api.restoreCandidateField(token, candidate.id, item.id, candidate.version); onChange(); }}>恢复旧值</Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="mt-auto flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
              {isCreator ? (
                <Select value={candidate.tier} onValueChange={handleTierChange} disabled={busy}>
                  <SelectTrigger className="w-full sm:w-44" aria-label="修改等级">
                    <SelectValue placeholder="选择等级" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIERS.map((t) => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Badge variant="outline" className="w-fit">
                  {TIERS.find((t) => t.value === candidate.tier)?.label || candidate.tier}
                </Badge>
              )}

              <div className="flex gap-2">
                {VOTE_TYPES.map(({ key, label, icon: Icon }) => {
                  const count = votesRevealed ? candidate[`${key}_count`] : undefined;
                  const active = userVote === key;
                  return (
                    <Button
                      key={key}
                      type="button"
                      variant={active ? "default" : "outline"}
                      size="sm"
                      disabled={busy}
                      onClick={() => handleVote(key)}
                      aria-pressed={active}
                      className="flex-1 sm:flex-none"
                    >
                      <Icon className={`mr-1 size-4 ${active ? "fill-current" : ""}`} />
                      <span className="text-xs">
                        {label}
                        {count !== undefined && ` (${count})`}
                      </span>
                    </Button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
