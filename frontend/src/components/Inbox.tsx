import { useEffect, useState } from "react";
import { RefreshCw, Check, X, Mail, ClipboardList, PhoneIncoming, Activity, Mic, ListTodo } from "lucide-react";
import { get, post } from "../api";
import { getTeamSession } from "../auth";
import Tickets from "./Tickets";

interface InboxData {
  emails: { id: number; kind: string; to_addr: string; subject: string; body: string; order_no: string; created_on: string; status: string; channel: string }[];
  claims: { id: string; order_no: string; sku: string; issue: string; status: string; decision_rule: string; remedy: string; estimated_cost_inr: number; created_on: string; channel: string; customer: string; details?: string; photos?: string; recommendation?: string; contact_phone?: string; decided_by?: string; decided_on?: string; decision_note?: string }[];
  callbacks: { id: number; phone: string; reason: string; status: string; created_on: string; channel: string }[];
  transcripts: { id: number; call_id: string; phone: string; started: string; transcript: string; summary: string; actions: string }[];
  audit: { id: number; ts: string; channel: string; actor: string; tool: string; args: string; result: string; rule: string; evidence: string }[];
  voice: { api_key: boolean; agent_id: string; phone_number: string; outbound_ready: boolean };
  tickets: { by_status: Record<string, number>; total: number };
}

/** "Tickets" — the internal team's console: the shared ticket queue plus claims, messages, call-backs, call transcripts and the audit log. */
export default function InboxView() {
  const [d, setD] = useState<InboxData | null>(null);
  const [tab, setTab] = useState<"queue" | "claims" | "emails" | "callbacks" | "transcripts" | "audit">("queue");
  const [leak, setLeak] = useState<{ restricted_to_cloud: number; calls: { provider: string; purpose: string; sensitivities: string[]; ms: number; model: string }[] } | null>(null);
  const load = () => { get<InboxData>("/actions/inbox").then(setD); get<typeof leak>("/audit").then(setLeak); };
  useEffect(load, []);
  if (!d) return <div className="p-6 muted">Loading…</div>;
  const pending = d.claims.filter((c) => c.status === "pending").length;
  const unread = d.emails.filter((e) => e.status === "unread").length;
  const team = getTeamSession();
  const active = (d.tickets?.by_status?.open || 0) + (d.tickets?.by_status?.in_progress || 0) + (d.tickets?.by_status?.waiting_customer || 0);

  return (
    <div className={`h-full ${tab === "queue" ? "flex flex-col" : "overflow-auto p-6 max-w-5xl mx-auto space-y-4"}`}>
      <div className={`flex items-center gap-3 flex-wrap ${tab === "queue" ? "px-6 pt-5" : ""}`}>
        <div className="text-lg font-medium">Tickets</div>
        <button className="btn small" onClick={load}><RefreshCw size={13} /> Refresh</button>
        <button className={`chip ${tab === "queue" ? "active" : ""}`} onClick={() => setTab("queue")} title="Open the ticket queue">{active} active ticket{active === 1 ? "" : "s"}</button>
        <button className={`chip ${tab === "claims" ? "active" : ""}`} onClick={() => setTab("claims")} title="Show claims">{pending} claim{pending === 1 ? "" : "s"} awaiting decision</button>
        <button className={`chip ${tab === "emails" ? "active" : ""}`} onClick={() => setTab("emails")} title="Show messages">{unread} unread</button>
        <span className={`chip ${d.voice.outbound_ready ? "done" : ""}`}><Mic size={12} /> voice line {d.voice.outbound_ready ? `live · ${d.voice.phone_number}` : "not deployed"}</span>
        {leak && <span className={`chip ${leak.restricted_to_cloud === 0 ? "done" : ""}`} title="Routing audit: restricted chunks sent to the cloud model">leak test: {leak.restricted_to_cloud} restricted → cloud</span>}
      </div>
      <div className={`flex border-b ${tab === "queue" ? "px-6 mt-3" : ""}`} style={{ borderColor: "var(--border)" }}>
        {([["queue", "Queue", <ListTodo size={13} />], ["claims", "Claims", <ClipboardList size={13} />], ["emails", "Emails", <Mail size={13} />], ["callbacks", "Call-backs", <PhoneIncoming size={13} />], ["transcripts", "Call transcripts", <Mic size={13} />], ["audit", "Audit log", <Activity size={13} />]] as const).map(([k, l, ic]) => (
          <div key={k} className={`tab flex items-center gap-1 ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>{ic} {l}</div>
        ))}
      </div>

      {tab === "queue" && (
        team ? <div className="flex-1 min-h-0"><Tickets key={team.id} /></div>
             : <div className="banner info text-sm">Sign in as a team member (top right) to take tickets, reply to customers and decide claims. Everything else on this page is visible without signing in.</div>
      )}

      {tab === "claims" && (
        <div className="space-y-2">
          {d.claims.length === 0 && <div className="muted text-sm">No claims yet.</div>}
          {d.claims.map((c) => {
            const details: Record<string, string> = (() => { try { return JSON.parse(c.details || "{}"); } catch { return {}; } })();
            const photos: string[] = (() => { try { return JSON.parse(c.photos || "[]"); } catch { return []; } })();
            return (
            <div key={c.id} className="panel p-3 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <b>{c.id}</b><span className="muted">{c.created_on.replace("T", " ")}</span>
                <span className={`chip ${c.status === "approved" ? "done" : c.status === "pending" ? "active" : ""}`}>{c.status}</span>
                <span className="chip">{c.channel}</span>
                <span className="ml-auto muted">est. ₹{c.estimated_cost_inr.toLocaleString("en-IN")}</span>
              </div>
              <div className="mt-1">{c.customer}{c.contact_phone ? ` · ${c.contact_phone}` : ""} · order {c.order_no} · {c.sku} — {c.issue}</div>
              {Object.keys(details).filter((k) => k !== "problem").length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 text-xs mt-1">
                  {Object.entries(details).filter(([k]) => k !== "problem").map(([k, v]) => <div key={k}><span className="muted">{k.replace("_", " ")}:</span> {v}</div>)}
                </div>
              )}
              {c.recommendation && <div className="text-xs mt-1"><span className="muted">System recommendation:</span> {c.recommendation}</div>}
              <div className="muted text-xs">Rule: {c.decision_rule}</div>
              <div className="muted text-xs">Remedy: {c.remedy}{c.decided_by ? ` · decided by ${c.decided_by} ${String(c.decided_on || "").replace("T", " ")}` : ""}{c.decision_note ? ` · ${c.decision_note}` : ""}</div>
              {photos.length > 0 ? (
                <div className="flex gap-2 mt-2 flex-wrap">{photos.map((p) => <a key={p} href={`/api/actions/claims/${c.id}/photo/${p}`} target="_blank" rel="noreferrer"><img src={`/api/actions/claims/${c.id}/photo/${p}`} alt={p} style={{ height: 72, borderRadius: 6, border: "1px solid var(--border)" }} /></a>)}</div>
              ) : <div className="muted text-xs mt-1">No photos yet — customer has the upload link (SMS / website).</div>}
              {c.status === "pending" && (
                <div className="mt-2 flex gap-2 items-center flex-wrap">
                  <input className="input" style={{ maxWidth: 320 }} placeholder="Note to the customer (optional)" id={`note-${c.id}`} />
                  <button className="btn small" onClick={() => post("/actions/inbox/decide_claim", { claim_id: c.id, decision: "approved", note: (document.getElementById(`note-${c.id}`) as HTMLInputElement)?.value || "" }).then(load)}><Check size={12} /> Approve</button>
                  <button className="btn small" onClick={() => post("/actions/inbox/decide_claim", { claim_id: c.id, decision: "declined", note: (document.getElementById(`note-${c.id}`) as HTMLInputElement)?.value || "" }).then(load)}><X size={12} /> Decline</button>
                  <span className="muted text-xs">The customer is notified by SMS + email; the claim's ticket is resolved.</span>
                </div>
              )}
            </div>
          ); })}
        </div>
      )}
      {tab === "emails" && (
        <div className="space-y-2">
          {d.emails.length === 0 && <div className="muted text-sm">No emails yet.</div>}
          {d.emails.map((e) => (
            <div key={e.id} className="panel p-3 text-sm" onClick={() => post("/actions/inbox/mark_read?inbox_id=" + e.id, {}).then(load)}>
              <div className="flex items-center gap-2"><b>{e.subject}</b><span className={`chip ${e.status === "unread" ? "active" : ""}`}>{e.status}</span><span className="chip">{e.kind}</span><span className="muted ml-auto text-xs">{e.created_on.replace("T", " ")}</span></div>
              <pre className="whitespace-pre-wrap font-sans text-sm mt-1 muted">{e.body}</pre>
            </div>
          ))}
        </div>
      )}
      {tab === "callbacks" && (
        <div className="space-y-2">
          {d.callbacks.length === 0 && <div className="muted text-sm">No call-back requests.</div>}
          {d.callbacks.map((c) => <div key={c.id} className="panel p-3 text-sm"><b>{c.phone}</b> · {c.reason} <span className="chip ml-2">{c.status}</span><span className="muted text-xs ml-2">{c.created_on.replace("T", " ")} · {c.channel}</span></div>)}
        </div>
      )}
      {tab === "transcripts" && (
        <div className="space-y-2">
          {d.transcripts.length === 0 && <div className="muted text-sm">No call transcripts yet — they arrive from the Sarvam voice agent's end-of-call webhook.</div>}
          {d.transcripts.map((t) => {
            const meta: { duration?: number } = (() => { try { return JSON.parse(t.actions || "{}"); } catch { return {}; } })();
            return (
              <div key={t.id} className="panel p-3 text-sm">
                <div className="flex items-center gap-2 flex-wrap"><b>Call {t.call_id}</b> · {t.phone} · {t.started?.replace("T", " ").slice(0, 16)}{meta.duration ? ` · ${Math.round(meta.duration)} s` : ""}</div>
                <div className="muted mt-1">{t.summary}</div>
                <details className="mt-2"><summary className="cursor-pointer text-xs muted">Transcript</summary><pre className="code mt-2">{t.transcript}</pre></details>
              </div>
            );
          })}
        </div>
      )}
      {tab === "audit" && (
        <div className="space-y-1">
          {d.audit.map((a) => <div key={a.id} className="text-xs flex gap-2 flex-wrap"><span className="muted">{a.ts.replace("T", " ")}</span><span className="chip">{a.channel}</span><b>{a.tool}</b><span className="muted">{a.args}</span><span>→ {a.rule}</span></div>)}
        </div>
      )}
    </div>
  );
}
