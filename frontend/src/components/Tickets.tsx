import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Check, X, Hand, MessageSquareReply, StickyNote, CircleCheck, Filter, User, Camera, Search, Clock, BookOpenCheck, Cpu, Cloud, ChevronDown, ChevronRight, ArrowLeft, Phone, Package, FileText, History } from "lucide-react";
import { get, post } from "../api";
import { getTeamSession, setTeamSession } from "../auth";

interface Ticket { id: string; kind: string; customer_phone: string; customer_name: string; subject: string; body: string; status: string; priority: string; assigned_to: string | null; assignee_name: string | null; ref: string; order_no: string | null; channel: string; created_on: string; updated_on: string; resolved_on: string | null; }
interface Event { id: number; ts: string; actor: string; kind: string; text: string; }
interface ClaimRow { id: string; order_no: string; sku: string; issue: string; status: string; recommendation: string; details: string; photos: string; estimated_cost_inr: number; decision_note: string; decided_by: string; decided_on: string; decision_rule: string; }
interface CustomerCtx { name: string; phone: string; summary: string; last_summary: string; claims: { claim_id: string; status: string; next_step: string; sku: string }[]; orders: { order_no: string; order_date: string; status: string }[]; tickets?: { id: string; kind: string; subject: string; status: string }[]; }
interface TicketFull extends Ticket { events: Event[]; claim?: ClaimRow | null; customer?: CustomerCtx | null; }
interface Queue { me: { id: string; name: string; role: string }; stats: { by_status: Record<string, number>; active_by_kind: Record<string, number>; active_by_assignee: Record<string, number>; total: number }; employees: { id: string; name: string; role: string }[]; tickets: Ticket[]; }
interface PolicySource { id: string; title: string; doc_code?: string; version?: string; effective_date?: string; page?: number; section?: string; sensitivity: string; excerpt: string; }
interface PolicyAnswer { ok: boolean; question: string; answer: string; summary: string; sources: PolicySource[]; conflicts: { verdict: string; resolution: string; reason: string; a: string; b: string }[]; routing: { llm: string | null; model: string | null; restricted_chunks: number }; timings_ms: Record<string, number>; detail?: string; is_draft?: boolean; }

const KIND: Record<string, string> = { claim_review: "Warranty claim", customer_email: "Customer email", callback: "Call-back", product_query: "Product / info query", order_help: "Order help", other: "Other" };
const STATUS_CHIP: Record<string, string> = { open: "active", in_progress: "", waiting_customer: "warn", resolved: "done", closed: "done" };
const STATUS_LABEL: Record<string, string> = { open: "Open", in_progress: "In progress", waiting_customer: "Waiting on customer", resolved: "Resolved", closed: "Closed" };
const SLA_HOURS = 48; // "a specialist replies within 2 working days"
const SUGGESTED_QUESTIONS = [
  "Is this product still covered for this fault, and what remedy does the warranty policy prescribe?",
  "Which tier can approve this cost, and what is the SLA for the service visit?",
  "Are there exclusions (installation by a non-authorised plumber, misuse, water quality) that apply here?",
  "Draft the reply to the customer explaining the decision with the policy reference.",
];
const EVENT_LABEL: Record<string, string> = { created: "Created", assigned: "Assigned", note: "Internal note", reply: "Reply to customer", status: "Status", customer_message: "Customer wrote", decision: "Decision", photos: "Photos", policy_check: "Policy check", priority: "Priority" };

function ageOf(iso: string): { h: number; label: string; breach: boolean } {
  const h = Math.max(0, (Date.now() - new Date(iso + "Z").getTime()) / 36e5);
  const label = h < 1 ? `${Math.round(h * 60)} min` : h < 48 ? `${Math.round(h)} h` : `${Math.round(h / 24)} d`;
  return { h, label, breach: h > SLA_HOURS };
}
const fmt = (iso?: string | null) => (iso ? iso.replace("T", " ").slice(0, 16) : "");
const Row = ({ k, v }: { k: string; v: React.ReactNode }) => (v ? <div className="flex gap-3 text-sm"><span className="muted w-[150px] shrink-0">{k}</span><span className="min-w-0">{v}</span></div> : null);

export default function Tickets() {
  const me = getTeamSession();
  const [q, setQ] = useState<Queue | null>(null);
  const [status, setStatus] = useState("active");
  const [mine, setMine] = useState(false);
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [sel, setSel] = useState<TicketFull | null>(null);
  const [dtab, setDtab] = useState<"case" | "policy" | "history">("case");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [pq, setPq] = useState("");
  const [thread, setThread] = useState<PolicyAnswer[]>([]);
  const [draftBusy, setDraftBusy] = useState(false);
  const [pBusy, setPBusy] = useState(false);
  const [openSrc, setOpenSrc] = useState<string | null>(null);
  const [dossier, setDossier] = useState<{ parts: { title: string; text: string; scope?: string }[]; calls: number } | null>(null);
  const [showDossier, setShowDossier] = useState(false);
  const loadDossier = async (id: string) => { const d = await get<{ parts: { title: string; text: string; scope?: string }[]; calls: number }>(`/actions/team/tickets/${id}/dossier`); setDossier(d); };

  const load = useCallback(() => {
    get<Queue & { detail?: string }>(`/actions/team/tickets?status=${status}&mine=${mine}${kind ? `&kind=${kind}` : ""}`).then((d) => {
      const detail = (d as { detail?: string }).detail;
      if (detail) {
        if (/sign in/i.test(detail)) { setTeamSession(null); window.dispatchEvent(new Event("kohler:team-login")); }
        setErr(detail);
      } else { setErr(""); setQ(d); }
    }).catch((e) => setErr(String(e)));
  }, [status, mine, kind]);
  useEffect(load, [load]);

  const open = async (id: string) => {
    const t = await get<TicketFull>(`/actions/team/tickets/${id}`);
    if (sel?.id !== id) {
      setPq(""); setDtab("case");
      // restore the policy-check conversation from the ticket history
      const restored: PolicyAnswer[] = (t.events || []).filter((e) => e.kind === "policy_check" && e.text.startsWith("Q: ")).map((e) => {
        const [qPart, rest = ""] = e.text.split("\nA: ");
        const answer = rest.split("\nSources:")[0];
        const srcLine = (rest.split("\nSources:")[1] || "").split("\n")[0].trim();
        return { ok: true, question: qPart.slice(3), answer, summary: "", sources: srcLine ? srcLine.split("; ").map((title, i) => ({ id: `s${i + 1}`, title, sensitivity: "", excerpt: "" })) : [], conflicts: [], routing: { llm: e.text.includes("(model: local)") ? "local" : "openai", model: null, restricted_chunks: 0 }, timings_ms: {}, restored: true } as PolicyAnswer & { restored?: boolean };
      });
      setThread(restored);
    }
    setSel(t); setText("");
    loadDossier(id).catch(() => {});
  };
  const back = () => { setSel(null); setDossier(null); load(); };
  const act = async (path: string, body: Record<string, unknown> = {}) => {
    if (!sel) return; setBusy(true);
    const r = await post<{ ok?: boolean; message?: string; detail?: string }>(`/actions/team/tickets/${sel.id}/${path}`, body);
    setBusy(false);
    if (r.ok === false || r.detail) { setErr(r.message || r.detail || "failed"); return; }
    setText(""); await open(sel.id); load();
  };
  const askPolicy = async (question: string) => {
    if (!sel || !question.trim()) return;
    setPBusy(true); setPq("");
    const r = await post<PolicyAnswer>(`/actions/team/tickets/${sel.id}/ask`, { question });
    setPBusy(false);
    if (r.detail) { setErr(r.detail); return; }
    setThread((th) => [...th, r]);
    const t = await get<TicketFull>(`/actions/team/tickets/${sel.id}`); setSel(t);
  };
  const draftReply = async () => {
    if (!sel) return; setDraftBusy(true);
    const r = await post<{ ok?: boolean; draft?: string; detail?: string; llm?: string }>(`/actions/team/tickets/${sel.id}/draft_reply`, {
      thread: thread.map((x) => ({ question: x.question, answer: x.answer, llm: x.routing.llm })), decision: sel.claim?.status || "" });
    setDraftBusy(false);
    if (r.detail || !r.draft) { setErr(r.detail || "draft failed"); return; }
    setText(r.draft); setDtab("history");
    const t = await get<TicketFull>(`/actions/team/tickets/${sel.id}`); setSel(t);
  };

  if (!me) return <div className="p-6 muted">Sign in as a team member to see the ticket queue.</div>;

  // ─────────────────────────── detail page ───────────────────────────
  if (sel) {
    const details: Record<string, string> = sel.claim ? (() => { try { return JSON.parse(sel.claim!.details || "{}"); } catch { return {}; } })() : {};
    const photos: string[] = sel.claim ? (() => { try { return JSON.parse(sel.claim!.photos || "[]"); } catch { return []; } })() : [];
    const closed = sel.status === "resolved" || sel.status === "closed";
    const age = ageOf(sel.created_on);
    return (
      <div className="h-full overflow-auto">
        <div className="max-w-5xl mx-auto p-6 space-y-4">
          <button className="btn small" onClick={back}><ArrowLeft size={13} /> Back to queue</button>

          {/* header */}
          <div className="panel p-5 space-y-3">
            <div className="flex items-start gap-3 flex-wrap">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xl font-medium">{sel.id}</span>
                  <span className="chip">{KIND[sel.kind] || sel.kind}</span>
                  <span className={`chip ${STATUS_CHIP[sel.status] || ""}`}>{STATUS_LABEL[sel.status] || sel.status}</span>
                  {(sel.priority === "high" || sel.priority === "urgent") && <span className="chip warn">{sel.priority}</span>}
                  {!closed && <span className={`chip ${age.breach ? "lock" : ""}`}><Clock size={10} /> {age.label} old</span>}
                </div>
                <div className="text-lg mt-1">{sel.subject}</div>
                <div className="muted text-sm mt-1"><User size={13} className="inline" /> {sel.customer_name || "Unknown customer"} · <Phone size={12} className="inline" /> {sel.customer_phone || "—"} · via {sel.channel} · opened {fmt(sel.created_on)}{sel.order_no ? <> · <Package size={12} className="inline" /> order {sel.order_no}</> : null}</div>
              </div>
              <div className="ml-auto flex items-center gap-2 flex-wrap">
                {q && !closed && (
                  <select className="input text-xs" style={{ width: "auto" }} value={sel.assigned_to || ""} onChange={(e) => e.target.value && act("take", { assignee: e.target.value })} title="Assignee">
                    <option value="">{sel.assignee_name ? `Assigned: ${sel.assignee_name}` : "Unassigned — assign to…"}</option>
                    {q.employees.map((e) => <option key={e.id} value={e.id}>{e.name} — {e.role}</option>)}
                  </select>
                )}
                {!closed && <select className="input text-xs" style={{ width: "auto" }} value={sel.priority} onChange={(e) => act("priority", { text: e.target.value })} title="Priority">{["low", "normal", "high", "urgent"].map((p) => <option key={p} value={p}>{p} priority</option>)}</select>}
                {sel.assigned_to !== me.id && !closed && <button className="btn small primary" disabled={busy} onClick={() => act("take")}><Hand size={12} /> Take</button>}
                {!closed && <button className="btn small" disabled={busy} onClick={() => act("status", { status: "resolved", text })}><CircleCheck size={12} /> Resolve</button>}
                {closed && <button className="btn small" disabled={busy} onClick={() => act("status", { status: "open", text: "reopened" })}>Reopen</button>}
              </div>
            </div>
            {err && <div className="banner lock text-xs">{err}</div>}
          </div>

          {/* tabs */}
          <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
            {([["case", "Case", <FileText size={13} />], ["policy", `Policy check${thread.length ? ` (${thread.length})` : ""}`, <BookOpenCheck size={13} />], ["history", `History & replies (${sel.events.length})`, <History size={13} />]] as const).map(([k, l, ic]) => (
              <div key={k} className={`tab flex items-center gap-1 ${dtab === k ? "on" : ""}`} onClick={() => setDtab(k)}>{ic} {l}</div>
            ))}
          </div>

          {dtab === "case" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <div className="panel p-5 space-y-3">
                  <div className="font-medium">Request</div>
                  <pre className="whitespace-pre-wrap font-sans text-sm">{sel.body}</pre>
                </div>
                {sel.claim && (
                  <div className="panel p-5 space-y-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="font-medium">Warranty claim {sel.claim.id}</div>
                      <span className={`chip ${sel.claim.status === "approved" ? "done" : sel.claim.status === "pending" ? "active" : ""}`}>{sel.claim.status}</span>
                      <span className="muted text-sm ml-auto">estimated ₹{sel.claim.estimated_cost_inr.toLocaleString("en-IN")}</span>
                    </div>
                    <div className="space-y-1">
                      <Row k="Product" v={`${sel.claim.sku} · order ${sel.claim.order_no}`} />
                      <Row k="Problem" v={sel.claim.issue} />
                      <Row k="Since when" v={details.since_when} />
                      <Row k="Symptoms" v={details.symptoms} />
                      <Row k="Installed by" v={details.installed_by} />
                      <Row k="Usage" v={details.usage} />
                      <Row k="Preferred visit" v={details.preferred_slot} />
                      <Row k="Contact" v={details.contact_phone} />
                    </div>
                    <div className="banner info text-sm"><b>System recommendation:</b> {sel.claim.recommendation}<div className="muted text-xs mt-1">{sel.claim.decision_rule}</div></div>
                    <div>
                      <div className="text-sm font-medium mb-1"><Camera size={13} className="inline" /> Photos</div>
                      {photos.length ? <div className="flex gap-2 flex-wrap">{photos.map((p) => <a key={p} href={`/api/actions/claims/${sel.claim!.id}/photo/${p}`} target="_blank" rel="noreferrer"><img src={`/api/actions/claims/${sel.claim!.id}/photo/${p}`} alt={p} style={{ height: 96, borderRadius: 8, border: "1px solid var(--border)" }} /></a>)}</div>
                        : <div className="muted text-sm">None yet — the customer has the upload link (SMS / website). Ask for them under History &amp; replies.</div>}
                    </div>
                    {sel.claim.status === "pending" ? (
                      <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                        <div className="text-sm font-medium">Decision</div>
                        <div className="muted text-xs">Only a person decides. Tip: run a policy check first — it is recorded on the ticket. The note below is sent to the customer with the decision (SMS + email).</div>
                        <textarea className="input" rows={2} placeholder="Note to the customer (e.g. fill-valve replacement under warranty; engineer visit Tuesday 10 am)" value={text} onChange={(e) => setText(e.target.value)} />
                        <div className="flex gap-2">
                          <button className="btn primary" disabled={busy} onClick={() => act("decide_claim", { decision: "approved", text })}><Check size={13} /> Approve claim</button>
                          <button className="btn" disabled={busy} onClick={() => act("decide_claim", { decision: "declined", text })}><X size={13} /> Decline claim</button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm pt-2 border-t" style={{ borderColor: "var(--border)" }}><b>{sel.claim.status}</b> by {sel.claim.decided_by} on {fmt(sel.claim.decided_on)}{sel.claim.decision_note ? ` — “${sel.claim.decision_note}”` : ""}</div>
                    )}
                  </div>
                )}
              </div>
              <div className="space-y-4">
                {sel.customer && (
                  <div className="panel p-5 space-y-2">
                    <div className="font-medium">Customer</div>
                    <div className="text-sm">{sel.customer.name || sel.customer_name || "Unknown"}<div className="muted">{sel.customer_phone}</div></div>
                    {sel.customer.last_summary && <div className="text-sm"><span className="muted">Last interaction:</span> {sel.customer.last_summary}</div>}
                    {sel.customer.orders?.length ? <div className="text-sm"><div className="muted">Orders</div>{sel.customer.orders.map((o) => <div key={o.order_no}>{o.order_no} · {o.order_date} · {o.status}</div>)}</div> : null}
                    {sel.customer.claims?.length ? <div className="text-sm"><div className="muted">Claims</div>{sel.customer.claims.map((c) => <div key={c.claim_id}>{c.claim_id} · {c.sku} · <span className={`chip ${c.status === "approved" ? "done" : c.status === "pending" ? "active" : ""}`}>{c.status}</span></div>)}</div> : null}
                    {sel.customer.tickets?.filter((t) => t.id !== sel.id).length ? <div className="text-sm"><div className="muted">Other tickets</div>{sel.customer.tickets!.filter((t) => t.id !== sel.id).map((t) => <div key={t.id}><button className="underline" onClick={() => open(t.id)}>{t.id}</button> · {t.subject.slice(0, 40)} · {STATUS_LABEL[t.status] || t.status}</div>)}</div> : null}
                  </div>
                )}
                <div className="panel p-5 space-y-2 text-sm">
                  <button className="flex items-center gap-2 font-medium w-full text-left" onClick={() => setShowDossier(!showDossier)}>{showDossier ? <ChevronDown size={14} /> : <ChevronRight size={14} />} What the assistant knows{dossier ? ` (${dossier.parts.length} sections${dossier.calls ? `, ${dossier.calls} call${dossier.calls === 1 ? "" : "s"}` : ""})` : ""}</button>
                  <div className="muted text-xs">This full case dossier — request, claim & coverage, photos, customer memory, call transcripts, ticket history — is attached to every policy question and every draft.</div>
                  {showDossier && dossier && (
                    <div className="space-y-3 pt-1">
                      <div><div className="text-xs font-medium" style={{ color: "var(--accent)" }}>Current case — what messages are about</div>
                        {dossier.parts.filter((p) => p.scope !== "background").map((p) => <div key={p.title} className="mt-1"><div className="text-xs font-medium">{p.title}</div><pre className="whitespace-pre-wrap font-sans text-xs muted" style={{ maxHeight: 200, overflow: "auto" }}>{p.text}</pre></div>)}</div>
                      {dossier.parts.some((p) => p.scope === "background") && <div><div className="text-xs font-medium muted">Background — reference only</div>
                        {dossier.parts.filter((p) => p.scope === "background").map((p) => <div key={p.title} className="mt-1"><div className="text-xs font-medium">{p.title}</div><pre className="whitespace-pre-wrap font-sans text-xs muted" style={{ maxHeight: 160, overflow: "auto" }}>{p.text}</pre></div>)}</div>}
                    </div>
                  )}
                </div>
                <div className="panel p-5 space-y-2 text-sm">
                  <div className="font-medium">Ticket</div>
                  <Row k="Assignee" v={sel.assignee_name || "unassigned"} />
                  <Row k="Priority" v={sel.priority} />
                  <Row k="Channel" v={sel.channel} />
                  <Row k="Opened" v={fmt(sel.created_on)} />
                  <Row k="Last update" v={fmt(sel.updated_on)} />
                  <Row k="Resolved" v={fmt(sel.resolved_on)} />
                </div>
              </div>
            </div>
          )}

          {dtab === "policy" && (
            <div className="space-y-4">
              <div className="panel p-5 space-y-2">
                <div className="flex items-center gap-2 font-medium"><BookOpenCheck size={16} /> Ask the internal knowledge base about this case</div>
                <div className="muted text-sm">A conversation: follow-up questions keep the context of the earlier turns. Case facts (order, product, coverage window, registration, cost, the customer's answers) are attached automatically; every turn is saved to the ticket history. When you are done, draft the customer reply from the whole thread.</div>
                {thread.length === 0 && <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">{SUGGESTED_QUESTIONS.slice(0, 3).map((sq) => <button key={sq} className="btn text-left text-sm" style={{ whiteSpace: "normal", lineHeight: 1.4 }} onClick={() => askPolicy(sq)} disabled={pBusy}>{sq}</button>)}</div>}
              </div>

              {thread.map((turn, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-end">
                    <div className="panel p-3 text-sm" style={{ maxWidth: "75%", background: "var(--accent-bg)", borderColor: "transparent" }}><span className="muted text-xs block mb-1">{me.name} asked</span>{turn.question}</div>
                  </div>
                  <div className="panel p-4 space-y-3">
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      <span className="muted">{turn.is_draft || /\(draft written from/.test(turn.sources.map((x) => x.title).join(" ")) ? "Draft message for the customer" : "Knowledge assistant"}</span>
                      <span className={`chip ml-auto ${turn.routing.llm === "local" ? "warn" : "done"}`}>{turn.routing.llm === "local" ? <Cpu size={11} /> : <Cloud size={11} />} {turn.routing.llm === "local" ? "on-device model (restricted evidence)" : "cloud model"}{turn.routing.model ? ` · ${turn.routing.model}` : ""}</span>
                    </div>
                    {turn.conflicts.map((c, j) => <div key={j} className="banner warn text-sm"><b>{c.verdict.replace("_", " ")}:</b> {c.resolution} <span className="muted">— {c.reason}</span></div>)}
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{turn.answer}</div>
                    {(turn.is_draft || /\(draft written from/.test(turn.sources.map((x) => x.title).join(" "))) && (
                      <div className="flex gap-2 items-center"><button className="btn small primary" onClick={() => { setText(turn.answer); setDtab("history"); }}><MessageSquareReply size={12} /> Use as reply to customer</button><span className="muted text-xs">opens in History &amp; replies — edit, then send</span></div>
                    )}
                    {turn.sources.length > 0 && !/\(draft written from/.test(turn.sources.map((x) => x.title).join(" ")) && (
                      <div>
                        <div className="text-xs font-medium mb-1 muted">Sources</div>
                        <div className="space-y-1">
                          {turn.sources.map((src) => (
                            <div key={`${i}-${src.id}`} className="text-xs">
                              <button className="inline-flex items-center gap-1 text-left" onClick={() => setOpenSrc(openSrc === `${i}-${src.id}` ? null : `${i}-${src.id}`)} disabled={!src.excerpt}>
                                {src.excerpt ? (openSrc === `${i}-${src.id}` ? <ChevronDown size={12} /> : <ChevronRight size={12} />) : <span style={{ width: 12 }} />}
                                <b>[{src.id}]</b> {src.title}{src.doc_code ? ` (${src.doc_code})` : ""}{src.version ? ` · v${src.version}` : ""}{src.page ? ` · p.${src.page}` : ""}{src.section ? ` · ${src.section}` : ""}
                                {src.sensitivity && <span className={`chip ${src.sensitivity === "restricted" ? "lock" : ""}`}>{src.sensitivity}</span>}
                              </button>
                              {openSrc === `${i}-${src.id}` && src.excerpt && <pre className="code mt-1 whitespace-pre-wrap">{src.excerpt}</pre>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {pBusy && <div className="panel p-3 text-sm muted">Routing → retrieving policy documents → reasoning… (about 10–20 s; longer if restricted documents route it on-device)</div>}

              <div className="panel p-4 space-y-2">
                {thread.length > 0 && <div className="flex flex-wrap gap-1">{SUGGESTED_QUESTIONS.filter((sq) => !thread.some((t) => t.question === sq)).slice(0, 3).map((sq) => <button key={sq} className="chip" onClick={() => askPolicy(sq)} disabled={pBusy}>{sq.length > 70 ? sq.slice(0, 70) + "…" : sq}</button>)}</div>}
                <div className="flex gap-2 items-center">
                  <input className="input flex-1" placeholder={thread.length ? "Ask a follow-up…" : "Ask a question about coverage, exclusions, authority, SLA…"} value={pq} onChange={(e) => setPq(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") askPolicy(pq); }} disabled={pBusy} />
                  <button className="btn primary" style={{ whiteSpace: "nowrap" }} disabled={pBusy || !pq.trim()} onClick={() => askPolicy(pq)}>{pBusy ? "Checking…" : "Ask"}</button>
                </div>
                {thread.length > 0 && (
                  <div className="flex items-center gap-2 justify-end pt-1 border-t" style={{ borderColor: "var(--border)" }}>
                    <span className="muted text-xs">Done researching? Write the customer reply from all {thread.length} question{thread.length === 1 ? "" : "s"} above{thread.some((t) => t.routing.llm === "local") ? " (on-device — the thread touched restricted documents)" : ""}.</span>
                    <button className="btn" style={{ whiteSpace: "nowrap" }} disabled={draftBusy || pBusy} onClick={draftReply}><MessageSquareReply size={13} /> {draftBusy ? "Drafting…" : "Draft reply from this thread"}</button>
                  </div>
                )}
              </div>
            </div>
          )}

          {dtab === "history" && (
            <div className="space-y-4">
              <div className="panel p-5 space-y-2">
                <div className="font-medium">Write to the customer or the team</div>
                <textarea className="input" rows={4} placeholder="A reply is sent to the customer by SMS + email and remembered by the chat and phone assistants. An internal note stays on the ticket." value={text} onChange={(e) => setText(e.target.value)} />
                <div className="flex gap-2 flex-wrap">
                  <button className="btn primary" disabled={busy || !text.trim()} onClick={() => act("reply", { text })}><MessageSquareReply size={13} /> Reply to customer</button>
                  <button className="btn" disabled={busy || !text.trim()} onClick={() => act("note", { text })}><StickyNote size={13} /> Add internal note</button>
                </div>
              </div>
              <div className="panel p-5">
                <div className="font-medium mb-3">History</div>
                <div className="space-y-3">
                  {[...sel.events].reverse().map((e) => (
                    <div key={e.id} className="flex gap-3 text-sm">
                      <div className="w-[120px] shrink-0 muted text-xs pt-0.5">{fmt(e.ts)}</div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2"><span className={`chip ${e.kind === "reply" ? "done" : e.kind === "customer_message" ? "active" : e.kind === "decision" ? "warn" : e.kind === "policy_check" ? "active" : ""}`}>{EVENT_LABEL[e.kind] || e.kind}</span><b>{e.actor}</b></div>
                        <div className="whitespace-pre-wrap mt-1">{e.text}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─────────────────────────── queue page ───────────────────────────
  const list = (q?.tickets || []).filter((t) => !search || [t.id, t.customer_name, t.customer_phone, t.subject, t.ref].join(" ").toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="h-full overflow-auto">
      <div className="max-w-5xl mx-auto p-6 space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="text-lg font-medium">Queue</div>
          <button className="btn small" onClick={load}><RefreshCw size={13} /> Refresh</button>
          <span className="muted text-sm ml-auto"><User size={13} className="inline" /> {me.name} · {me.role}</span>
        </div>
        {q && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[["open", "Open"], ["in_progress", "In progress"], ["waiting_customer", "Waiting on customer"], ["resolved", "Resolved"]].map(([k, l]) => (
              <button key={k} className="panel p-4 text-left" style={status === k ? { outline: "2px solid var(--accent)" } : {}} onClick={() => setStatus(status === k ? "active" : k)}>
                <div className="text-2xl font-medium">{q.stats.by_status[k] || 0}</div><div className="muted text-sm">{l}</div>
              </button>
            ))}
          </div>
        )}
        {q && (
          <div className="flex flex-wrap gap-1 text-xs">
            {Object.entries(q.stats.active_by_kind).map(([k, n]) => <span key={k} className="chip">{KIND[k] || k}: {n}</span>)}
            {Object.entries(q.stats.active_by_assignee).map(([k, n]) => <span key={k} className="chip">{k === "unassigned" ? "unassigned" : (q.employees.find((e) => e.id === k)?.name || k)}: {n}</span>)}
          </div>
        )}
        <div className="flex items-center gap-2 flex-wrap text-sm">
          <Filter size={13} />
          <select className="input" style={{ width: "auto" }} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">Active (open + in progress + waiting)</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="waiting_customer">Waiting on customer</option><option value="resolved">Resolved</option><option value="closed">Closed</option><option value="all">All (history)</option>
          </select>
          <select className="input" style={{ width: "auto" }} value={kind} onChange={(e) => setKind(e.target.value)}><option value="">All kinds</option>{Object.entries(KIND).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          <label className="flex items-center gap-1"><input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> Mine</label>
          <span className="inline-flex items-center gap-1 flex-1 min-w-[200px]"><Search size={13} /><input className="input" placeholder="Search id, customer, phone, subject…" value={search} onChange={(e) => setSearch(e.target.value)} /></span>
        </div>
        {err && <div className="banner lock text-sm">{err}</div>}

        <div className="panel" style={{ overflow: "hidden" }}>
          <div className="grid text-xs muted px-4 py-2 border-b" style={{ gridTemplateColumns: "120px 1fr 190px 130px 150px 90px", borderColor: "var(--border)" }}>
            <div>Ticket</div><div>Subject</div><div>Customer</div><div>Status</div><div>Assignee</div><div>Age</div>
          </div>
          {list.length === 0 && <div className="muted text-sm p-4">Nothing here.</div>}
          {list.map((t) => {
            const a = ageOf(t.created_on); const closed = t.status === "resolved" || t.status === "closed";
            return (
              <div key={t.id} className="grid items-center px-4 py-3 text-sm border-b cursor-pointer hover:opacity-90" style={{ gridTemplateColumns: "120px 1fr 190px 130px 150px 90px", borderColor: "var(--border)" }} onClick={() => open(t.id)}>
                <div><b>{t.id}</b><div className="muted text-xs">{KIND[t.kind] || t.kind}</div></div>
                <div className="min-w-0 pr-3"><div className="truncate">{t.subject}</div><div className="muted text-xs">via {t.channel} · {fmt(t.created_on)}{(t.priority === "high" || t.priority === "urgent") ? <span className="chip warn ml-2">{t.priority}</span> : null}</div></div>
                <div className="min-w-0"><div className="truncate">{t.customer_name || "Unknown"}</div><div className="muted text-xs">{t.customer_phone}</div></div>
                <div><span className={`chip ${STATUS_CHIP[t.status] || ""}`}>{STATUS_LABEL[t.status] || t.status}</span></div>
                <div className="muted text-xs truncate">{t.assignee_name || "unassigned"}</div>
                <div>{!closed && <span className={`chip ${a.breach ? "lock" : ""}`}><Clock size={10} /> {a.label}</span>}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
