import { useState } from "react";
import { LogIn, X } from "lucide-react";
import { post } from "../api";
import { setSession, type Session } from "../auth";

/** Prototype login: any 10-digit mobile number + the demo password (1234). Questions never need it; actions do. */
export default function Login({ onClose, reason }: { onClose: () => void; reason?: string }) {
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    const r = await post<Session & { ok?: boolean; message?: string; detail?: string }>("/actions/login", { phone, password, name });
    setBusy(false);
    if (!r.token) { setErr(r.message || r.detail || "Login failed"); return; }
    setSession({ token: r.token, phone: r.phone, name: r.name, known: r.known });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,.45)" }} onClick={onClose}>
      <form className="panel p-5 w-[360px] max-w-[92vw] space-y-3" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="flex items-center gap-2"><LogIn size={16} /><div className="font-medium">Sign in to Kohler Assist</div><button type="button" className="btn small ml-auto" onClick={onClose}><X size={13} /></button></div>
        {reason && <div className="banner info text-xs">{reason}</div>}
        <div className="muted text-xs">Questions do not need an account. Sign in to register products, raise claims, order, upload photos and see your messages — on the website and on the phone line, we remember where you left off.</div>
        <input className="input" placeholder="Mobile number (10 digits)" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="numeric" autoFocus />
        <input className="input" placeholder="Your name (first time only)" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <div className="banner lock text-xs">{err}</div>}
        <button className="btn primary w-full" disabled={busy || phone.replace(/\D/g, "").length < 10 || !password}>Sign in</button>
        <div className="muted text-xs">Prototype: password is <span className="mono">1234</span> for every number. Demo customer: <span className="mono">9810000101</span> (Rohan Mehta).</div>
      </form>
    </div>
  );
}
