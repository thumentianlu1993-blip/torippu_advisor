import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const root = resolve(process.cwd());
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("stabilize-current-mvp frontend contract", () => {
  it("uses share-token routes, credentials cookies, and no creator secret in browser state", () => {
    const api = read("lib/api.ts");
    const reportPage = read("app/p/[token]/page.tsx");

    expect(api).toContain('credentials: "include"');
    expect(api).not.toMatch(/\/api\/projects\/\$\{(?:id|projectId)\}/);
    expect(api).not.toContain("X-Creator-Token");
    expect(api).not.toContain("x-session-id");
    expect(reportPage).not.toContain('searchParams.get("creator_token")');
    expect(reportPage).not.toContain("localStorage");
    expect(reportPage).not.toContain("project.id");
  });

  it("provides the creator recovery, manual edit, vote visibility, and merge review UI", () => {
    for (const component of [
      "app/components/RecoveryKeyPrompt.tsx",
      "app/components/ManualCandidateEditor.tsx",
      "app/components/VoteVisibilityControl.tsx",
      "app/components/MergeReviewQueue.tsx",
    ]) {
      expect(existsSync(resolve(root, component)), `${component} is required`).toBe(true);
    }
  });

  it("shows coverage state and never renders raw provider errors", () => {
    const coveragePath = "app/components/CoverageStatus.tsx";
    expect(existsSync(resolve(root, coveragePath)), `${coveragePath} is required`).toBe(true);
    const coverage = read(coveragePath);
    expect(coverage).toContain("coverage");
    expect(coverage).not.toContain("raw_error");
    expect(coverage).not.toContain("stack");
  });
});
