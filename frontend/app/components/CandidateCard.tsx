"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const TIERS = ["must_go", "strongly_recommended", "optional", "resource_pool", "discarded"];

export default function CandidateCard({
  candidate,
  projectId,
  isCreator,
  votesRevealed,
  onChange,
}: {
  candidate: any;
  projectId: number;
  isCreator: boolean;
  votesRevealed: boolean;
  onChange: () => void;
}) {
  const [userVote, setUserVote] = useState(candidate.user_vote || null);

  const handleVote = async (voteType: string) => {
    try {
      await api.vote(candidate.id, voteType);
      setUserVote(voteType);
      onChange();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleTierChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    try {
      await api.updateCandidate(projectId, candidate.id, { tier: e.target.value });
      onChange();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this candidate?")) return;
    try {
      await api.deleteCandidate(projectId, candidate.id);
      onChange();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg">{candidate.name}</h3>
          <p className="text-sm text-gray-600">{candidate.area || "No area"} · {candidate.category} · ⭐ {candidate.rating ?? "-"}</p>
          {candidate.summary && <p className="text-sm mt-1 text-gray-700">{candidate.summary}</p>}
        </div>
        {isCreator && (
          <button onClick={handleDelete} className="text-red-500 text-sm">Delete</button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2 items-center">
        {isCreator ? (
          <select
            value={candidate.tier}
            onChange={handleTierChange}
            className="border rounded px-2 py-1 text-sm"
          >
            {TIERS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        ) : (
          <span className="text-xs px-2 py-1 bg-gray-100 rounded">{candidate.tier}</span>
        )}

        <div className="flex gap-2 ml-auto">
          {["like", "dislike", "neutral"].map((vt) => (
            <button
              key={vt}
              onClick={() => handleVote(vt)}
              className={`text-sm px-3 py-1 rounded border ${
                userVote === vt ? "bg-blue-100 border-blue-400" : "bg-white"
              }`}
            >
              {vt} {votesRevealed && candidate[`${vt}_count`] !== undefined ? `(${candidate[`${vt}_count`]})` : ""}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
