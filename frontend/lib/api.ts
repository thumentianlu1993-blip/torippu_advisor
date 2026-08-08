const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;
const API_URL = configuredApiUrl === "same-origin"
  ? ""
  : configuredApiUrl || "http://localhost:8000";

async function fetchJson(url: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${url}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || `HTTP ${res.status}`);
  if (res.status === 204) return null;
  return res.json();
}

export type Project = {
  destination: string; duration_days: number; departure: string; travel_time?: string;
  traveler_structure?: string; preferences?: string; budget_level?: string;
  constraints?: string; votes_revealed: boolean; status?: string;
};
export type ProjectCreated = Project & { share_token: string; recovery_key: string };
export type Report = { status: string; progress: number; content: Record<string, any> };
export type Candidate = {
  id: number; version: number; name: string; category: string; tier: string; area?: string;
  rating?: number; price_level?: number; summary?: string; opening_hours?: string;
  image_url?: string; source_url?: string; notes?: string; user_vote?: string | null; like_count?: number;
  dislike_count?: number; neutral_count?: number;
};

const scoped = (token: string, path = "") => `/api/projects/by-token/${encodeURIComponent(token)}${path}`;

export const api = {
  createProject: (data: any) => fetchJson("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  getProjectByToken: (token: string) => fetchJson(scoped(token)),
  getProjectStatus: (token: string) => fetchJson(scoped(token, "/status")),
  getReport: (token: string) => fetchJson(scoped(token, "/report")),
  getCandidates: (token: string, params?: Record<string, string>) => {
    const query = params ? `?${new URLSearchParams(params)}` : "";
    return fetchJson(scoped(token, `/candidates${query}`));
  },
  creatorCheck: (token: string) => fetchJson(scoped(token, "/creator-check")),
  addCandidate: (token: string, data: any) => fetchJson(scoped(token, "/creator/candidates"), { method: "POST", body: JSON.stringify(data) }),
  updateCandidate: (token: string, candidateId: number, data: any) => fetchJson(scoped(token, `/creator/candidates/${candidateId}`), { method: "PATCH", body: JSON.stringify(data) }),
  getCandidateHistory: (token: string, candidateId: number) => fetchJson(scoped(token, `/creator/candidates/${candidateId}/history`)),
  restoreCandidateField: (token: string, candidateId: number, changeId: number, version: number) => fetchJson(scoped(token, `/creator/candidates/${candidateId}/restore`), { method: "POST", body: JSON.stringify({ change_id: changeId, version }) }),
  deleteCandidate: (token: string, candidateId: number) => fetchJson(scoped(token, `/creator/candidates/${candidateId}`), { method: "DELETE", body: "{}" }),
  vote: (token: string, candidateId: number, voteType: string) => fetchJson(scoped(token, `/candidates/${candidateId}/votes`), { method: "POST", body: JSON.stringify({ vote_type: voteType }) }),
  setVotesVisibility: (token: string, revealed: boolean) => fetchJson(scoped(token, "/creator/votes-visibility"), { method: "PATCH", body: JSON.stringify({ revealed }) }),
  getCreatorCoverage: (token: string) => fetchJson(scoped(token, "/creator/coverage")),
  getMergeProposals: (token: string) => fetchJson(scoped(token, "/creator/merge-proposals")),
  decideMerge: (token: string, id: number, decision: string) => fetchJson(scoped(token, `/creator/merge-proposals/${id}/decision`), { method: "POST", body: JSON.stringify({ decision }) }),
  exportGoogleMaps: (token: string, creator = false) => fetchJson(scoped(token, creator ? "/creator/export/google-maps" : "/export/google-maps")),
  recollect: (token: string) => fetchJson(scoped(token, "/recollect"), { method: "POST", body: "{}" }),
  rotateShare: (token: string) => fetchJson(scoped(token, "/creator/share-rotation"), { method: "POST", body: "{}" }),
  deleteProject: (token: string) => fetchJson(scoped(token, "/delete"), { method: "POST", body: "{}" }),
  recoverProject: (token: string, recoveryKey: string) => fetchJson(scoped(token, "/recover"), { method: "POST", body: JSON.stringify({ recovery_key: recoveryKey }) }),
  streamReport: (token: string) => new EventSource(`${API_URL}${scoped(token, "/report/stream")}`, { withCredentials: true }),
};
