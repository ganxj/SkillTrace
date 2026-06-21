export const API_BASE_URL =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_BASE_URL ??
      (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}/api/v1` : undefined) ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "/api/v1"
    : process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export type DomainPack = {
  id: string;
  slug: string;
  name: string;
  version: string;
  description: string;
};

export type CourseSummary = {
  domain: DomainPack;
  skillCount: number;
  questionCount: number;
  skills: Skill[];
};

export type QuizQuestion = {
  prompt: string;
  options: string[];
  correct_index: number;
  explanation: string;
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
  lesson_explain: string;
  key_points: string[];
  questions: QuizQuestion[];
  order_index: number;
  prerequisites: string[];
};

export type ContentImport = {
  id: string;
  filename: string;
  content_type: string;
  file_sha256: string;
  status: string;
  error: string;
  domain_id: string | null;
  total_segments: number;
  processed_segments: number;
  control_requested: string;
  current_step: string;
  created_at: string;
  completed_at: string | null;
  domain: DomainPack | null;
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
    throw new Error(await apiErrorMessage(response, `API ${path} failed`));
  }
  return readApiJson<T>(response);
}

export async function readApiJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API returned non-JSON response (${response.status}): ${text.slice(0, 300)}`);
  }
}

export async function apiErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await readApiJson<{ detail?: string }>(response);
    return payload.detail ?? `${fallback}: ${response.status}`;
  } catch (error) {
    return error instanceof Error ? error.message : `${fallback}: ${response.status}`;
  }
}

export async function getDashboardData() {
  const domains = await fetchJson<DomainPack[]>("/domains");
  const latestDomain = domains.length === 0 ? null : await fetchJson<DomainPack>("/domains/latest");
  const [skills, states, evidence, imports] = await Promise.all([
    latestDomain ? fetchJson<Skill[]>(`/skills?domain_slug=${latestDomain.slug}`) : Promise.resolve([]),
    fetchJson<LearnerState[]>("/learner/state"),
    fetchJson<Evidence[]>("/evidence?limit=12"),
    fetchJson<ContentImport[]>("/imports")
  ]);
  const courseSummaries = await Promise.all(
    domains.map(async (domain) => {
      const domainSkills = await fetchJson<Skill[]>(`/skills?domain_slug=${domain.slug}`);
      return {
        domain,
        skillCount: domainSkills.length,
        questionCount: domainSkills.reduce((sum, skill) => sum + skill.questions.length, 0),
        skills: domainSkills
      };
    })
  );
  return { domains, latestDomain, skills, states, evidence, imports, courseSummaries };
}
