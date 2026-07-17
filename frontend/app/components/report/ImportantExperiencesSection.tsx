import CandidateList from "@/app/components/CandidateList";
import { Gem } from "lucide-react";

export default function ImportantExperiencesSection({
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
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-terracotta-700">
        <div className="flex size-8 items-center justify-center rounded-lg bg-terracotta-50">
          <Gem className="size-4" />
        </div>
        <h2 className="font-heading text-xl font-semibold">重要体验</h2>
      </div>
      <CandidateList
        candidates={candidates}
        projectId={projectId}
        isCreator={isCreator}
        votesRevealed={votesRevealed}
        onChange={onChange}
      />
    </div>
  );
}
