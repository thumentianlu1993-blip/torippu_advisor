"use client";

import { useState } from "react";
import CandidateCard from "./CandidateCard";

const SECTIONS = [
  { key: "core", label: "Core" },
  { key: "natural", label: "Natural" },
  { key: "cultural", label: "Cultural" },
  { key: "entertainment", label: "Entertainment" },
  { key: "shopping", label: "Shopping" },
  { key: "local_specialty", label: "Local Specialty" },
  { key: "personal_preference", label: "Preference" },
  { key: "niche", label: "Niche" },
  { key: "food", label: "Food" },
  { key: "lodging", label: "Lodging" },
];

export default function CandidateList({
  candidates,
  projectId,
  isCreator,
  votesRevealed,
  onChange,
}: {
  candidates: any[];
  projectId: number;
  isCreator: boolean;
  votesRevealed: boolean;
  onChange: () => void;
}) {
  const [filter, setFilter] = useState({ category: "", tier: "", search: "" });

  const filtered = candidates.filter((c) => {
    if (filter.category && c.category !== filter.category) return false;
    if (filter.tier && c.tier !== filter.tier) return false;
    if (filter.search && !c.name.toLowerCase().includes(filter.search.toLowerCase())) return false;
    return true;
  });

  const tiers = Array.from(new Set(candidates.map((c) => c.tier)));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search candidates..."
          value={filter.search}
          onChange={(e) => setFilter({ ...filter, search: e.target.value })}
          className="border rounded px-3 py-2 text-sm"
        />
        <select
          value={filter.category}
          onChange={(e) => setFilter({ ...filter, category: e.target.value })}
          className="border rounded px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          {SECTIONS.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <select
          value={filter.tier}
          onChange={(e) => setFilter({ ...filter, tier: e.target.value })}
          className="border rounded px-3 py-2 text-sm"
        >
          <option value="">All tiers</option>
          {tiers.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-gray-500">No candidates match your filters.</p>
      ) : (
        <div className="grid gap-3">
          {filtered.map((c) => (
            <CandidateCard
              key={c.id}
              candidate={c}
              projectId={projectId}
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
