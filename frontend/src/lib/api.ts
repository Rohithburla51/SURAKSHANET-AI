/**
 * frontend/src/lib/api.ts
 * ────────────────────────
 * SurakshaNet AI — Typed async API client
 * Centralises every fetch call so pages never hard-code URLs or handle
 * raw Response objects.  All functions throw on non-2xx.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function _handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body — use status text
      detail = res.statusText || detail;
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared types — mirror the Pydantic schemas exactly
// ─────────────────────────────────────────────────────────────────────────────

export interface RAGMatch {
  category: string;
  similarity: number;
  excerpt: string;
}

export interface ScamAnalysisResult {
  risk_score: number;            // 0–100
  category: string;
  confidence: number;            // 0.0–1.0
  verdict: "SCAM" | "LIKELY_SCAM" | "UNCERTAIN" | "SAFE";
  manipulation_tactics: string[];
  red_flags: string[];
  explanation: string;
  explanation_hi: string;
  recommended_actions: string[];
  rag_matches_used: RAGMatch[];
  model_used: string;
  processing_time_ms: number;
}

export interface OpenCVMetrics {
  clahe_contrast_score: number;
  fft_watermark_opacity: number;
  laplacian_variance: number;
  sobel_edge_density: number;
  bleed_line_count: number;
}

export interface CounterfeitResult {
  verdict: "GENUINE" | "SUSPECT" | "COUNTERFEIT";
  final_score: number;
  confidence: number;
  denomination: number;
  features_passed: string[];
  features_failed: string[];
  opencv_metrics: OpenCVMetrics;
  explanation: string;
  recommended_actions: string[];
  model_used: string;
  processing_time_ms: number;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface NetworkQueryResult {
  question: string;
  cypher_query: string;
  query_explanation: string;
  is_safe: boolean;
  summary: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  row_count: number;
  model_used: string;
  processing_time_ms: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Scam Analysis
// ─────────────────────────────────────────────────────────────────────────────

/** Analyse a plain-text message for scam indicators. */
export async function analyzeScam(text: string, sessionId?: string): Promise<ScamAnalysisResult> {
  const res = await fetch(`${BASE_URL}/api/scam/analyze/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, session_id: sessionId ?? undefined }),
  });
  return _handleResponse<ScamAnalysisResult>(res);
}

/** Analyse an audio recording for scam indicators (multipart upload). */
export async function analyzeScamAudio(
  file: File,
  sessionId?: string,
): Promise<ScamAnalysisResult> {
  const form = new FormData();
  form.append("audio", file);
  if (sessionId) form.append("session_id", sessionId);

  const res = await fetch(`${BASE_URL}/api/scam/analyze/audio`, {
    method: "POST",
    body: form,
  });
  return _handleResponse<ScamAnalysisResult>(res);
}

// ─────────────────────────────────────────────────────────────────────────────
// Counterfeit Detection
// ─────────────────────────────────────────────────────────────────────────────

export async function scanNote(
  image: File,
  denomination?: number,
  branchCode?: string,
): Promise<CounterfeitResult> {
  const form = new FormData();
  form.append("image", image);
  if (denomination !== undefined) form.append("denomination", String(denomination));
  if (branchCode) form.append("branch_code", branchCode);

  const res = await fetch(`${BASE_URL}/api/counterfeit/scan`, {
    method: "POST",
    body: form,
  });
  return _handleResponse<CounterfeitResult>(res);
}

// ─────────────────────────────────────────────────────────────────────────────
// Network / Police Intelligence
// ─────────────────────────────────────────────────────────────────────────────

export async function queryNetwork(question: string): Promise<NetworkQueryResult> {
  const res = await fetch(`${BASE_URL}/api/network/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return _handleResponse<NetworkQueryResult>(res);
}

export async function tracePhone(
  phoneNumber: string,
  hops = 3,
): Promise<NetworkQueryResult> {
  const encoded = encodeURIComponent(phoneNumber);
  const res = await fetch(`${BASE_URL}/api/network/trace/phone/${encoded}?hops=${hops}`);
  return _handleResponse<NetworkQueryResult>(res);
}

export async function traceAccount(
  accountId: string,
  hops = 3,
): Promise<NetworkQueryResult> {
  const encoded = encodeURIComponent(accountId);
  const res = await fetch(`${BASE_URL}/api/network/trace/account/${encoded}?hops=${hops}`);
  return _handleResponse<NetworkQueryResult>(res);
}
