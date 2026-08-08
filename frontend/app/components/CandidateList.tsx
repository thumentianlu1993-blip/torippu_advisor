"use client";

import { useEffect, useMemo, useState } from "react";
import CandidateCard from "./CandidateCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
  SheetClose,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, SlidersHorizontal, ArrowUpDown, X } from "lucide-react";

const CATEGORIES = [
  { key: "core", label: "核心体验" },
  { key: "natural", label: "自然风光" },
  { key: "cultural", label: "人文历史" },
  { key: "entertainment", label: "娱乐" },
  { key: "shopping", label: "购物" },
  { key: "local_specialty", label: "当地特色" },
  { key: "personal_preference", label: "个人偏好" },
  { key: "niche", label: "小众" },
  { key: "food", label: "美食" },
  { key: "lodging", label: "住宿" },
];

const SORT_OPTIONS = [
  { value: "tier", label: "推荐等级" },
  { value: "rating", label: "评分" },
  { value: "name", label: "名称" },
  { value: "area", label: "区域" },
];

const TIER_ORDER = ["must_go", "strongly_recommended", "optional", "resource_pool", "discarded"];

function useDebounce(value: string, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function CandidateList({
  candidates,
  token,
  isCreator,
  votesRevealed,
  onChange,
}: {
  candidates: any[];
  token: string;
  isCreator: boolean;
  votesRevealed: boolean;
  onChange: () => void;
}) {
  const [filter, setFilter] = useState({
    category: "",
    tier: "",
    area: "",
    price_level: "",
    search: "",
  });
  const [sortBy, setSortBy] = useState("tier");
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 250);

  useEffect(() => {
    setFilter((prev) => ({ ...prev, search: debouncedSearch }));
  }, [debouncedSearch]);

  const tiers = useMemo(
    () => Array.from(new Set(candidates.map((c) => c.tier).filter(Boolean))),
    [candidates]
  );
  const areas = useMemo(
    () => Array.from(new Set(candidates.map((c) => c.area).filter(Boolean))),
    [candidates]
  );
  const priceLevels = useMemo(
    () =>
      Array.from(
        new Set(candidates.map((c) => c.price_level).filter((p) => p !== null && p !== undefined))
      ).sort(),
    [candidates]
  );

  const activeFilterCount = useMemo(() => {
    return Object.entries(filter).filter(([key, value]) => key !== "search" && value !== "").length;
  }, [filter]);

  const filtered = useMemo(() => {
    const list = candidates.filter((c) => {
      if (filter.category && c.category !== filter.category) return false;
      if (filter.tier && c.tier !== filter.tier) return false;
      if (filter.area && !(c.area || "").toLowerCase().includes(filter.area.toLowerCase())) return false;
      if (filter.price_level && String(c.price_level) !== filter.price_level) return false;
      if (filter.search && !c.name.toLowerCase().includes(filter.search.toLowerCase())) return false;
      return true;
    });

    return [...list].sort((a, b) => {
      switch (sortBy) {
        case "rating":
          return (b.rating ?? 0) - (a.rating ?? 0);
        case "name":
          return a.name.localeCompare(b.name);
        case "area":
          return (a.area || "").localeCompare(b.area || "");
        case "tier":
        default: {
          const ai = TIER_ORDER.indexOf(a.tier);
          const bi = TIER_ORDER.indexOf(b.tier);
          if (ai !== bi) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
          return a.name.localeCompare(b.name);
        }
      }
    });
  }, [candidates, filter, sortBy]);

  const clearFilters = () => {
    setFilter({ category: "", tier: "", area: "", price_level: "", search: "" });
    setSearchInput("");
  };

  const FilterFields = ({ inSheet = false }: { inSheet?: boolean }) => (
    <div className={`space-y-4 ${inSheet ? "" : "hidden lg:grid lg:grid-cols-5 lg:gap-3"}`}>
      <div className={inSheet ? "" : "lg:col-span-2"}>
        <label className="mb-1.5 block text-xs font-medium">搜索</label>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索地点..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium">类别</label>
        <Select value={filter.category} onValueChange={(value) => setFilter({ ...filter, category: value || "" })}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="全部分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部分类</SelectItem>
            {CATEGORIES.map((s) => (
              <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium">等级</label>
        <Select value={filter.tier} onValueChange={(value) => setFilter({ ...filter, tier: value || "" })}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="全部等级" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部等级</SelectItem>
            {tiers.map((t) => (
              <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium">区域</label>
        <Select value={filter.area} onValueChange={(value) => setFilter({ ...filter, area: value || "" })}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="全部区域" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部区域</SelectItem>
            {areas.map((a) => (
              <SelectItem key={a} value={a}>{a}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-medium">价格</label>
        <Select value={filter.price_level} onValueChange={(value) => setFilter({ ...filter, price_level: value || "" })}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="全部价格" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部价格</SelectItem>
            {priceLevels.map((p) => (
              <SelectItem key={p} value={String(p)}>{"$".repeat(Number(p) + 1)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Mobile search + filter sheet */}
      <div className="flex items-center gap-2 lg:hidden">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>
        <Sheet>
          <SheetTrigger
            render={
              <Button variant="outline" size="icon" className="relative">
                <SlidersHorizontal className="size-4" />
                {activeFilterCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
                    {activeFilterCount}
                  </span>
                )}
              </Button>
            }
          />
          <SheetContent side="bottom" className="rounded-t-2xl">
            <SheetHeader>
              <SheetTitle>筛选</SheetTitle>
            </SheetHeader>
            <div className="py-4">
              <FilterFields inSheet />
            </div>
            <SheetFooter className="flex-row">
              <SheetClose
                render={<Button variant="outline" className="flex-1">关闭</Button>}
              />
              <Button onClick={clearFilters} variant="ghost" className="flex-1">
                <X className="mr-1 size-4" /> 清除
              </Button>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      </div>

      {/* Desktop filter bar */}
      <FilterFields />

      {/* Sort + results meta */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {filtered.length} 个结果
        </p>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-7 text-xs">
              <X className="mr-1 size-3" /> 清除筛选
            </Button>
          )}
          <div className="flex items-center gap-1">
            <ArrowUpDown className="size-3.5 text-muted-foreground" />
            <Select value={sortBy} onValueChange={(value) => setSortBy(value || "tier")}>
              <SelectTrigger className="h-7 w-32 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value} className="text-xs">{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center">
          <p className="text-sm text-muted-foreground">没有匹配的候选。</p>
          <Button variant="link" size="sm" onClick={clearFilters} className="mt-2">
            清除全部筛选
          </Button>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((c) => (
            <CandidateCard
              key={c.id}
              candidate={c}
              token={token}
              isCreator={isCreator}
              votesRevealed={votesRevealed}
              onChange={onChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}
