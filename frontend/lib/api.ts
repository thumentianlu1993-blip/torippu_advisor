const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sessionId = document.cookie
    .split("; ")
    .find((row) => row.startsWith("session_id="))
    ?.split("=")[1];
  if (!sessionId) {
    sessionId = generateSessionId();
    document.cookie = `session_id=${sessionId}; path=/; max-age=31536000`;
  }
  return sessionId;
}

async function fetchJson(url: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "x-session-id": getSessionId(),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export type Project = {
  id: number;
  token: string;
  /** Only present in the POST /api/projects creation response. */
  creator_token?: string;
  destination: string;
  duration_days: number;
  departure: string;
  travel_time?: string;
  traveler_structure?: string;
  preferences?: string;
  budget_level?: string;
  constraints?: string;
  votes_revealed: boolean;
  status?: string;
};

export type Report = {
  status: string;
  progress: number;
  content: Record<string, any>;
};

export type Candidate = {
  id: number;
  name: string;
  category: string;
  tier: string;
  area?: string;
  rating?: number;
  price_level?: number;
  summary?: string;
  opening_hours?: string;
  image_url?: string;
  user_vote?: string | null;
  like_count?: number;
  dislike_count?: number;
  neutral_count?: number;
};

export const api = {
  createProject: (data: any) =>
    fetchJson("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getProjectByToken: (token: string) => fetchJson(`/api/projects/by-token/${token}`),
  getProjectStatus: (token: string) => fetchJson(`/api/projects/by-token/${token}/status`),
  getReport: (token: string) => fetchJson(`/api/projects/by-token/${token}/report`),
  getCandidates: (token: string, params?: Record<string, string>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchJson(`/api/projects/by-token/${token}/candidates${query}`);
  },
  addCandidate: (id: number, data: any, creatorToken: string) =>
    fetchJson(`/api/projects/${id}/candidates`, {
      method: "POST",
      body: JSON.stringify(data),
      headers: { "X-Creator-Token": creatorToken },
    }),
  updateCandidate: (projectId: number, candidateId: number, data: any, creatorToken: string) =>
    fetchJson(`/api/projects/${projectId}/candidates/${candidateId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
      headers: { "X-Creator-Token": creatorToken },
    }),
  deleteCandidate: (projectId: number, candidateId: number, creatorToken: string) =>
    fetchJson(`/api/projects/${projectId}/candidates/${candidateId}`, {
      method: "DELETE",
      headers: { "X-Creator-Token": creatorToken },
    }),
  creatorCheck: (token: string, creatorToken: string) =>
    fetchJson(`/api/projects/by-token/${token}/creator-check`, {
      headers: { "X-Creator-Token": creatorToken },
    }),
  vote: (candidateId: number, voteType: string) =>
    fetchJson(`/api/candidates/${candidateId}/votes`, {
      method: "POST",
      body: JSON.stringify({ vote_type: voteType }),
    }),
  exportGoogleMaps: (token: string) =>
    fetchJson(`/api/projects/by-token/${token}/export/google-maps`),
  recollect: (token: string, creatorToken: string) =>
    fetchJson(`/api/projects/by-token/${token}/recollect`, {
      method: "POST",
      headers: { "X-Creator-Token": creatorToken },
    }),

  streamReport: (projectId: number) => {
    const url = new URL(`${API_URL}/api/projects/${projectId}/report/stream`);
    url.searchParams.set("x-session-id", getSessionId());
    return new EventSource(url.toString());
  },
};
