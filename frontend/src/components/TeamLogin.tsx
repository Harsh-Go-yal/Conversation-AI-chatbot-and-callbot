import { useEffect, useState } from "react";
import { LogIn, X } from "lucide-react";
import { get, post } from "../api";
import { setTeamSession } from "../auth";

interface Emp { id: string; name: string; role: string; team: string; tier: string; }

/** Internal team sign-in (prototype: pick an employee + demo password; SSO in production). */
export default function TeamLogin({ onClose }: { onClose: () => void }) {
  const [emps, setEmps] = useState<Emp[]>([]);
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { get<Emp[]>("/actions/team/employees").then((e) => { setEmps(e); if (e[0]) setId(e[0].id); }).catch(() => {}); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    const r = await post<{ ok?: boolean; token?: string; id: string; name: string; role: string; team: string; tier: string; message?: string; detail?: string }>("/actions/team/login", { employee_id: id, password });
    setBusy(false);
    if (!r.token) { setErr(r.message || r.detail || "Sign-in failed"); return; }
    setTeamSession({ token: r.token, id: r.id, name: r.name, role: r.role, team: r.team, tier: r.tier });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,.45)" }} onClick={onClose}>
      <form className="panel p-5 w-[380px] max-w-[92vw] space-y-3" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="flex items-center gap-2"><LogIn size={16} /><div className="font-medium">Internal team sign-in</div><button type="button" className="btn small ml-auto" onClick={onClose}><X size={13} /></button></div>
        <div className="muted text-xs">Every request from customers lands in one shared queue. Sign in to take tickets, reply to customers and decide claims — every step is recorded on the ticket.</div>
        <select className="input" value={id} onChange={(e) => setId(e.target.value)}>{emps.map((e) => <option key={e.id} value={e.id}>{e.name} — {e.role} ({e.tier})</option>)}</select>
        <input className="input" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
        {err && <div className="banner lock text-xs">{err}</div>}
        <button className="btn primary w-full" disabled={busy || !id || !password}>Sign in</button>
        <div className="muted text-xs">Prototype password: <span className="mono">1234</span>.</div>
      </form>
    </div>
  );
}
