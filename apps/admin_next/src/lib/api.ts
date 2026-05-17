const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type DomainPack = {
  id: string;
  slug: string;
  name: string;
  version: string;
  description: string;
};

export type Skill = {
  id: string;
  domain_id: string;
  slug: string;
  title: string;
  summary: string;
  kind: string;
  difficulty: number;
  estimated_minutes: number;
  content: string;
  order_index: number;
  prerequisites: string[];
};

export type LearnerState = {
  id: string;
  user_id: string;
  skill_id: string;
  mastery: number;
  confidence: number;
  last_seen_at: string | null;
  review_due_at: string | null;
  evidence_count: number;
  updated_at: string;
  skill: Skill | null;
};

export type Evidence = {
  id: string;
  user_id: string;
  skill_id: string;
  session_id: string | null;
  evidence_type: string;
  score: number;
  confidence_delta: number;
  mastery_delta: number;
  prompt: string;
  response: string;
  feedback: string;
  created_at: string;
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "X-User-Id": "demo-user" },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getDashboardData() {
  const [domains, skills, states, evidence] = await Promise.all([
    fetchJson<DomainPack[]>("/domains"),
    fetchJson<Skill[]>("/skills?domain_slug=quant_v1"),
    fetchJson<LearnerState[]>("/learner/state"),
    fetchJson<Evidence[]>("/evidence?limit=12")
  ]);
  return { domains, skills, states, evidence };
}

