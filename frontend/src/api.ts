// Thin client for the FastAPI backend (proxied at /api in dev).
import { authHeaders } from "./auth";
export type Persona = "customer" | "internal";
export type Fmt = "text" | "json" | "excel" | "xml" | "markdown_table" | "email";

export interface Source { id: string; title: string; domain: string; region: string; sensitivity: string; origin: string; doc_code?: string; version?: string; effective_date?: string; page?: number; section?: string; excerpt: string; }
export interface Claim { id: string; text: string; type: string; confidence: number; source_ids: string[]; }
export interface Conflict { source_a: string; source_b: string; verdict: string; resolution: string; reason: string; }
export interface AccessNote { kind: string; message: string; count?: number; }
export interface Routing { llm_used: "openai" | "local"; model: string; reason: string; restricted_chunks: number; stage_timings_ms: Record<string, number>; }
export interface IR { query: string; intent: string; persona: Persona; domains: string[]; requested_format: Fmt; claims: Claim[]; sources: Source[]; conflicts: Conflict[]; access_notes: AccessNote[]; summary: string; routing?: Routing; entities: Record<string, string[]>; }
export interface Output { format: string; content?: string; download_id?: string; filename?: string; validation?: { validated: boolean; attempts: number; schema: string; error?: string }; to?: string; subject?: string; body?: string; citations?: string[]; action_hint?: boolean; }
export interface StageEvent { stage: string; [k: string]: unknown; }

export async function* chatStream(body: { session_id?: string; persona: Persona; message: string; json_schema?: unknown }) {
  const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(body) });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, idx); buf = buf.slice(idx + 2);
      let event = "message"; let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) yield { event, data: JSON.parse(data) } as { event: string; data: Record<string, unknown> };
    }
  }
}

export async function convert(session_id: string, format: Fmt, json_schema?: unknown, recipient?: string): Promise<{ output: Output }> {
  const r = await fetch("/api/convert", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id, format, json_schema, recipient }) });
  if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
  return r.json();
}

export const downloadUrl = (id: string) => `/api/download/${id}`;

export async function post<T = Record<string, unknown>>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(body) });
  const j = await r.json();
  if (r.status === 401) return { ok: false, message: j.detail || "Please log in.", login_required: true } as T;
  return j;
}
export async function get<T = Record<string, unknown>>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`, { headers: authHeaders() });
  return r.json();
}
export async function upload<T = Record<string, unknown>>(path: string, files: FileList | File[]): Promise<T> {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  const r = await fetch(`/api${path}`, { method: "POST", headers: authHeaders(), body: fd });
  const j = await r.json();
  if (r.status === 401) return { ok: false, message: j.detail || "Please log in.", login_required: true } as T;
  return j;
}
