// Login state (prototype). Customer: mobile number + demo password → X-Customer-Token.
// Internal team: employee + demo password → X-Employee-Token. Both are kept in localStorage.
export interface Session { token: string; phone: string; name: string; known: boolean; }
export interface TeamSession { token: string; id: string; name: string; role: string; team: string; tier: string; }

const KEY = "kohler_customer_session";
const TKEY = "kohler_team_session";
const listeners = new Set<() => void>();

export function getSession(): Session | null {
  try { const raw = localStorage.getItem(KEY); return raw ? (JSON.parse(raw) as Session) : null; } catch { return null; }
}
export function setSession(s: Session | null) {
  try { if (s) localStorage.setItem(KEY, JSON.stringify(s)); else localStorage.removeItem(KEY); } catch { /* ignore */ }
  listeners.forEach((l) => l());
}
export function getTeamSession(): TeamSession | null {
  try { const raw = localStorage.getItem(TKEY); return raw ? (JSON.parse(raw) as TeamSession) : null; } catch { return null; }
}
export function setTeamSession(s: TeamSession | null) {
  try { if (s) localStorage.setItem(TKEY, JSON.stringify(s)); else localStorage.removeItem(TKEY); } catch { /* ignore */ }
  listeners.forEach((l) => l());
}
export function onSessionChange(l: () => void) { listeners.add(l); return () => { listeners.delete(l); }; }
export function authHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  const s = getSession(); if (s) h["X-Customer-Token"] = s.token;
  const t = getTeamSession(); if (t) h["X-Employee-Token"] = t.token;
  return h;
}
