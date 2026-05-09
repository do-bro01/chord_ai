const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface ApiErrorDetail {
  code: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, detail: ApiErrorDetail | string) {
    const parsed: ApiErrorDetail =
      typeof detail === "string"
        ? { code: "ERROR", message: detail }
        : detail;
    super(parsed.message);
    this.status = status;
    this.code = parsed.code;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const detail = data?.detail ?? "요청에 실패했습니다.";
    throw new ApiError(res.status, detail);
  }

  return data as T;
}

export interface User {
  id: string;
  email: string;
  provider: string;
  email_verified_at: string | null;
  created_at: string;
}

export interface BeatSlot {
  beat: string;          // '1' | '2' | '3' | '4'
  chord: string | null;  // null이면 직전 비트와 같은 코드 (지속)
  time: number;          // 비트 시각(초)
}

export interface Bar {
  index: number;
  start: number;
  end: number;
  beats: BeatSlot[];     // 비트 슬롯 (보통 4개)
  chords: string[];      // 호환용 — 이 마디 distinct 코드
}

export interface ExtractResult {
  filename: string;
  chords: string[];  // 호환용 — 전체 진행
  bars: Bar[];       // 마디 단위 그룹핑
}

export const audioApi = {
  extract: async (file: File): Promise<ExtractResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/audio/extract`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new ApiError(res.status, data?.detail ?? "코드 추출에 실패했습니다.");
    }
    return data as ExtractResult;
  },
};

// ============================================================================
// Arrange / Preview / Export (PRD v2 신규)
// ============================================================================

export type Genre = "City Pop" | "Jazz" | "Ballad" | "Lo-fi" | "Bossa Nova";
export type Complexity = "단순" | "보통" | "복잡";
export type Tension = "적음" | "보통" | "많음";
export type BassStyle = "루트 중심" | "부드러운 연결" | "워킹 베이스";
export type Rhythm = "안정적" | "싱코페이션" | "펑키함";

export interface ArrangementOptions {
  genre: Genre;
  complexity: Complexity;
  tension: Tension;
  bass_style: BassStyle;
  rhythm: Rhythm;
}

export interface ArrangeRequest {
  current_chords: string[];
  key: string;
  bpm: number;
  time_signature: string;
  section_size_bars: number;
  options: ArrangementOptions;
  free_text?: string | null;
}

export interface ChordValidation {
  label: string;
  normalized: string;
  music21_ok: boolean;
  membership: "diatonic" | "borrowed" | "foreign" | "unparseable";
  issue: string | null;
}

export interface ValidationReport {
  foreign_count: number;
  unparseable_count: number;
  music21_failures: string[];
  has_issues: boolean;
  chords: ChordValidation[];
}

export interface ArrangeResponse {
  chords: string[];
  rationale: string;
  warnings: string[];
  validation: ValidationReport;
}

export type ExportFormat = "musicxml" | "midi" | "pdf";

export interface ExportRequest {
  chords: string[];
  format: ExportFormat;
  bpm: number;
  beats_per_bar: number;
  title?: string;
}

async function fetchBinary(path: string, body: unknown): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    let detail: ApiErrorDetail | string = "요청에 실패했습니다.";
    try {
      const parsed = text ? JSON.parse(text) : null;
      if (parsed?.detail) detail = parsed.detail;
    } catch {
      detail = text || detail;
    }
    throw new ApiError(res.status, detail);
  }
  return res.blob();
}

export const arrangeApi = {
  arrange: (req: ArrangeRequest) =>
    apiFetch<ArrangeResponse>("/api/arrange", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  preview: (chords: string[], bpm: number, beatsPerBar: number) =>
    fetchBinary("/api/preview", {
      chords,
      bpm,
      beats_per_bar: beatsPerBar,
    }),

  export: (req: ExportRequest) => fetchBinary("/api/export", req),
};

export const authApi = {
  requestSignupCode: (email: string) =>
    apiFetch<void>("/auth/signup/request-code", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifySignup: (email: string, code: string, password: string) =>
    apiFetch<User>("/auth/signup/verify", {
      method: "POST",
      body: JSON.stringify({ email, code, password }),
    }),

  login: (email: string, password: string) =>
    apiFetch<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

  me: () => apiFetch<User>("/auth/me"),

  googleStartUrl: () => `${API_BASE}/auth/google/start`,
};
