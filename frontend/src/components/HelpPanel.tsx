import { useEffect, useState } from "react";
import { Phone, Mail, PhoneCall, ShieldCheck, Wrench, ShoppingCart, HelpCircle, Camera, LogIn, MessageSquareText, RefreshCw } from "lucide-react";
import { get, post, upload } from "../api";
import { getSession, onSessionChange } from "../auth";

interface Item { sku: string; name: string; category: string; qty: number; registered: number; }
interface Order { order_no: string; name: string; phone: string; email: string; order_date: string; status: string; total_inr: number; items: Item[]; }
interface ClaimCtx { claim_id: string; order_no: string; sku: string; issue: string; status: string; created_on: string; photos: number; missing_info: string[]; next_step: string; upload_url: string; decision_note: string; }
interface TicketCtx { id: string; kind: string; subject: string; status: string; updated_on: string; ref: string; last_update?: { kind: string; text: string; ts: string } | null; }
interface Ctx { ok: boolean; known: boolean; name: string; orders: { order_no: string; order_date: string; status: string }[]; claims: ClaimCtx[]; tickets?: TicketCtx[]; last_summary: string; summary: string; }
interface Msg { id: number; kind: string; subject: string; body: string; created_on: string; channel: string; }
type Need = "register" | "claim" | "help" | "order" | "other";

const INTAKE: { k: string; label: string; ph: string }[] = [
  { k: "since_when", label: "Since when?", ph: "e.g. since last Tuesday" },
  { k: "symptoms", label: "Symptoms", ph: "constant or intermittent; error lights, noise, leakage…" },
  { k: "installed_by", label: "Installed by / when", ph: "Kohler-authorised installer, 2022" },
  { k: "usage", label: "Usage", ph: "residential / commercial" },
  { k: "preferred_slot", label: "Preferred visit slot", ph: "e.g. Saturday morning" },
];

export default function HelpPanel() {
  const [session, setSession] = useState(getSession());
  useEffect(() => onSessionChange(() => setSession(getSession())), []);
  const [ctx, setCtx] = useState<Ctx | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [orderNo, setOrderNo] = useState("");
  const [orders, setOrders] = useState<Order[]>([]);
  const [order, setOrder] = useState<Order | null>(null);
  const [sku, setSku] = useState("");
  const [need, setNeed] = useState<Need | null>(null);
  const [issue, setIssue] = useState("");
  const [intake, setIntake] = useState<Record<string, string>>({});
  const [files, setFiles] = useState<FileList | null>(null);
  const [ask, setAsk] = useState({ subject: "", body: "", kind: "product_query" });
  const [ticketReply, setTicketReply] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [voice, setVoice] = useState<{ phone_number?: string; outbound_ready?: boolean }>({});
  const [products, setProducts] = useState<{ sku: string; name: string; price_inr: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState({ subject: "", body: "" });

  const loadMe = () => {
    if (!getSession()) { setCtx(null); setMsgs([]); return; }
    get<{ context: Ctx }>("/actions/me").then((d) => setCtx(d.context || null)).catch(() => {});
    get<Msg[]>("/actions/my_messages").then((m) => setMsgs(Array.isArray(m) ? m : [])).catch(() => {});
  };
  useEffect(() => {
    get<{ voice: { phone_number?: string; outbound_ready?: boolean } }>("/actions/inbox").then((d) => setVoice(d.voice || {})).catch(() => {});
    get<{ sku: string; name: string; price_inr: number }[]>("/actions/products").then(setProducts).catch(() => {});
  }, []);
  useEffect(loadMe, [session]);

  const askLogin = () => window.dispatchEvent(new Event("kohler:login"));

  async function lookup(byPhone = false) {
    setBusy(true); setResult(null);
    const r = await post<{ ok: boolean; orders: Order[]; message: string; login_required?: boolean }>("/actions/lookup_order", byPhone ? { phone: session?.phone } : { order_no: orderNo });
    if (r.login_required) { askLogin(); setBusy(false); return; }
    setOrders(r.orders || []); setOrder(r.orders?.[0] || null); setSku(r.orders?.[0]?.items?.[0]?.sku || "");
    if (!r.ok) setResult({ message: r.message });
    setBusy(false);
  }

  async function act() {
    if (!session) { askLogin(); return; }
    if (!order && need !== "order" && need !== "other") return;
    setBusy(true);
    let r: Record<string, unknown> = {};
    if (need === "register") r = await post("/actions/register_warranty", { order_no: order!.order_no, sku });
    else if (need === "claim") {
      r = await post("/actions/open_claim", { order_no: order!.order_no, sku, issue: issue || "Product defect reported by customer", ...intake, contact_phone: session.phone });
      if (r.claim_id && files && files.length) {
        const up = await upload<{ ok: boolean; message: string }>(`/actions/claims/${r.claim_id}/photos`, files);
        r = { ...r, message: `${r.message} ${up.message || ""}` };
      }
    }
    else if (need === "help") r = await post("/actions/check_warranty", { order_no: order!.order_no, sku, issue });
    else if (need === "order") r = await post("/actions/place_order", { sku, qty: 1, phone: session.phone, address: "as per profile" });
    else if (need === "other") r = await post("/actions/ask_team", { subject: ask.subject || "Question for the team", body: ask.body, kind: ask.kind, order_no: order?.order_no });
    if ((r as { login_required?: boolean }).login_required) askLogin();
    setResult(r); setBusy(false); loadMe();
    setEmail({ subject: `${need === "claim" ? "Warranty claim" : need === "register" ? "Warranty registration" : need === "order" ? "New order" : "Product help"} — order ${order?.order_no || ""}`, body: `Hello Kohler India Customer Care,\n\nOrder: ${order?.order_no || "(new)"}\nProduct: ${sku}\n${issue ? `Issue: ${issue}\n` : ""}\n${(r.message as string) || ""}\n\nPlease contact me at ${session.phone}.\n\nThank you,\n${order?.name || session.name || ""}` });
  }

  async function addPhotos(claimId: string, fl: FileList | null) {
    if (!fl || !fl.length) return;
    setBusy(true);
    const r = await upload<{ ok: boolean; message: string }>(`/actions/claims/${claimId}/photos`, fl);
    setResult(r); setBusy(false); loadMe();
  }

  async function sendEmail() {
    if (!session) { askLogin(); return; }
    setBusy(true);
    const r = await post("/actions/send_email", { subject: email.subject, body: email.body, order_no: order?.order_no, from_addr: order?.email || "customer@example.in" });
    setResult(r); setBusy(false);
  }

  async function callMe() {
    if (!session) { askLogin(); return; }
    setBusy(true);
    const r = await post("/actions/request_callback", { phone: session.phone, reason: `${need || "help"}: ${issue || sku || "general"}` });
    setResult(r); setBusy(false);
  }

  const NEEDS: { k: Need; label: string; icon: React.ReactNode }[] = [
    { k: "register", label: "Register warranty", icon: <ShieldCheck size={15} /> },
    { k: "claim", label: "Claim warranty", icon: <Wrench size={15} /> },
    { k: "help", label: "Check coverage / product help", icon: <HelpCircle size={15} /> },
    { k: "order", label: "Order a product", icon: <ShoppingCart size={15} /> },
    { k: "other", label: "Ask the team (product info / anything else)", icon: <MessageSquareText size={15} /> },
  ];

  return (
    <div className="h-full overflow-auto p-6 max-w-4xl mx-auto space-y-4">
      <div>
        <div className="text-lg font-medium">Help with my product</div>
        <div className="muted text-sm">Register, claim, check coverage or order — then email the team or talk to our voice assistant. Every claim is reviewed and decided by a Kohler Customer Care specialist. (Demo data: order <span className="mono">KI-2022-0412</span>, customer <span className="mono">9810000101</span>, password <span className="mono">1234</span>.)</div>
      </div>

      {!session ? (
        <div className="panel p-4 flex items-center gap-3 flex-wrap">
          <LogIn size={16} />
          <div className="text-sm">Sign in with your mobile number to register products, raise claims, upload photos and see your messages. Questions in the chat never need a login.</div>
          <button className="btn primary ml-auto" onClick={askLogin}>Sign in</button>
        </div>
      ) : (
        <div className="panel p-4 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-sm font-medium">Welcome back{ctx?.name ? `, ${ctx.name}` : ""} · {session.phone}</div>
            <button className="btn small ml-auto" onClick={loadMe}><RefreshCw size={12} /> Refresh</button>
          </div>
          {ctx?.last_summary && <div className="muted text-sm">Last time: {ctx.last_summary}</div>}
          {ctx?.claims?.length ? ctx.claims.map((c) => (
            <div key={c.claim_id} className="banner info text-sm">
              <div><b>Claim {c.claim_id}</b> · {c.sku} · <span className={`chip ${c.status === "approved" ? "done" : ""}`}>{c.status}</span> <span className="muted">{c.created_on.replace("T", " ")}</span></div>
              <div className="muted">{c.issue}</div>
              <div className="mt-1">{c.next_step}{c.decision_note ? ` Note from Customer Care: ${c.decision_note}` : ""}</div>
              {c.missing_info.length > 0 && <div className="muted text-xs mt-1">Still needed: {c.missing_info.join(", ")}</div>}
              {c.status === "pending" && (
                <label className="btn small mt-2 inline-flex items-center gap-1 cursor-pointer"><Camera size={12} /> {c.photos ? `Add more photos (${c.photos} uploaded)` : "Upload photos"}
                  <input type="file" accept="image/*" multiple hidden onChange={(e) => addPhotos(c.claim_id, e.target.files)} />
                </label>
              )}
            </div>
          )) : <div className="muted text-sm">No open claims on this number.</div>}
          {ctx?.tickets?.filter((t) => !(t.ref || "").startsWith("CLM-")).length ? (
            <div className="space-y-2">
              <div className="text-sm font-medium">My requests</div>
              {ctx.tickets!.filter((t) => !(t.ref || "").startsWith("CLM-")).map((t) => (
                <div key={t.id} className="banner info text-sm">
                  <div><b>{t.id}</b> · {t.subject} · <span className="chip">{t.status.replace("_", " ")}</span> <span className="muted text-xs">{t.updated_on.replace("T", " ")}</span></div>
                  {t.last_update?.kind === "reply" && <div className="mt-1">Team: {t.last_update.text}</div>}
                  {t.status !== "closed" && (
                    <div className="flex gap-2 mt-2">
                      <input className="input" placeholder="Reply to the team…" value={ticketReply[t.id] || ""} onChange={(e) => setTicketReply({ ...ticketReply, [t.id]: e.target.value })} />
                      <button className="btn small" disabled={busy || !(ticketReply[t.id] || "").trim()} onClick={async () => { setBusy(true); await post("/actions/ticket_message", { ticket_id: t.id, text: ticketReply[t.id] }); setTicketReply({ ...ticketReply, [t.id]: "" }); setBusy(false); loadMe(); }}>Send</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : null}
          {msgs.length > 0 && (
            <details className="text-sm"><summary className="cursor-pointer">My messages ({msgs.length}) — SMS / email follow-ups we sent you</summary>
              <div className="space-y-2 mt-2">{msgs.map((m) => <div key={m.id} className="panel p-2"><div className="text-xs muted">{m.created_on.replace("T", " ")} · {m.kind.replace("customer_", "")} · via {m.channel}</div><pre className="whitespace-pre-wrap font-sans text-sm mt-1">{m.body}</pre></div>)}</div>
            </details>
          )}
        </div>
      )}

      <div className="panel p-4 space-y-3">
        <div className="text-sm font-medium">1 · Find your order</div>
        <div className="flex gap-2 flex-wrap">
          <input className="input flex-1 min-w-[180px]" placeholder="Order number (KI-YYYY-NNNN)" value={orderNo} onChange={(e) => setOrderNo(e.target.value)} />
          <button className="btn" onClick={() => lookup(false)} disabled={busy || !orderNo}>Look up</button>
          <button className="btn" onClick={() => (session ? lookup(true) : askLogin())} disabled={busy}>My orders (by my number)</button>
        </div>
        {orders.length > 0 && (
          <div className="space-y-2">
            {orders.length > 1 && <select className="input" value={order?.order_no || ""} onChange={(e) => { const o = orders.find((x) => x.order_no === e.target.value) || null; setOrder(o); setSku(o?.items?.[0]?.sku || ""); }}>{orders.map((o) => <option key={o.order_no} value={o.order_no}>{o.order_no} · {o.order_date}</option>)}</select>}
            {order && (
              <div className="banner info text-sm">
                <div><b>{order.order_no}</b> · {order.name} · {order.order_date} · {order.status}</div>
                <select className="input mt-2" value={sku} onChange={(e) => setSku(e.target.value)}>{order.items.map((i) => <option key={i.sku} value={i.sku}>{i.sku} · {i.name}{i.registered ? " · registered" : ""}</option>)}</select>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="panel p-4 space-y-3">
        <div className="text-sm font-medium">2 · What do you need?</div>
        <div className="flex flex-wrap gap-2">{NEEDS.map((n) => <button key={n.k} className={`btn ${need === n.k ? "primary" : ""}`} onClick={() => setNeed(n.k)}>{n.icon} {n.label}</button>)}</div>
        {need === "order" && <select className="input" value={sku} onChange={(e) => setSku(e.target.value)}><option value="">Choose a product…</option>{products.map((p) => <option key={p.sku} value={p.sku}>{p.sku} · {p.name} · ₹{p.price_inr.toLocaleString("en-IN")}</option>)}</select>}
        {(need === "claim" || need === "help") && <input className="input" placeholder="What exactly is wrong? (e.g. control panel has no power)" value={issue} onChange={(e) => setIssue(e.target.value)} />}
        {need === "other" && (
          <div className="space-y-2">
            <div className="muted text-xs">Goes to the Kohler Customer Care queue; a team member picks it up and replies by SMS/email within 2 working days. Needs your mobile number (sign in).</div>
            <select className="input" value={ask.kind} onChange={(e) => setAsk({ ...ask, kind: e.target.value })}><option value="product_query">Product information / buying advice</option><option value="order_help">Help with an order</option><option value="other">Something else</option></select>
            <input className="input" placeholder="Subject" value={ask.subject} onChange={(e) => setAsk({ ...ask, subject: e.target.value })} />
            <textarea className="input" rows={4} placeholder="Your question or request" value={ask.body} onChange={(e) => setAsk({ ...ask, body: e.target.value })} />
          </div>
        )}
        {need === "claim" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {INTAKE.map((f) => <label key={f.k} className="text-xs muted">{f.label}<input className="input mt-1" placeholder={f.ph} value={intake[f.k] || ""} onChange={(e) => setIntake({ ...intake, [f.k]: e.target.value })} /></label>)}
            <label className="text-xs muted md:col-span-2"><Camera size={12} className="inline mr-1" />Photos of the product, the fault and the model label (optional now — you can add them later)
              <input className="input mt-1" type="file" accept="image/*" multiple onChange={(e) => setFiles(e.target.files)} /></label>
          </div>
        )}
        {need && <button className="btn primary" onClick={act} disabled={busy || (!order && need !== "order" && need !== "other") || (need === "other" && !ask.body.trim())}>{session ? "Proceed" : "Sign in to proceed"}</button>}
        {result && (
          <div className={`banner ${result.ok === false ? "lock" : "info"} text-sm`}>
            <div>{String(result.message)}</div>
            {"rule" in result && result.rule ? <div className="muted text-xs mt-1">Rule applied: {String(result.rule)}</div> : null}
            {"claim_id" in result && <div className="text-xs mt-1">Claim {String(result.claim_id)} · status <b>{String(result.status)}</b> — a Customer Care specialist will decide; you will get an SMS and email.</div>}
            {"ticket_id" in result && !("claim_id" in result) && <div className="text-xs mt-1">Ticket {String(result.ticket_id)} — track it below under “My requests”.</div>}
            {"voice" in result && <div className="text-xs mt-1">Voice: {String((result.voice as { message?: string; status?: string }).message || (result.voice as { status?: string }).status)}</div>}
          </div>
        )}
      </div>

      <div className="panel p-4 space-y-3">
        <div className="text-sm font-medium">3 · How do you want to proceed?</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <div className="font-medium text-sm flex items-center gap-2"><Mail size={15} /> Email the internal team</div>
            <input className="input" value={email.subject} onChange={(e) => setEmail({ ...email, subject: e.target.value })} placeholder="Subject" />
            <textarea className="input" rows={7} value={email.body} onChange={(e) => setEmail({ ...email, body: e.target.value })} placeholder="Message" />
            <button className="btn" onClick={sendEmail} disabled={busy || !email.subject}>{session ? "Send to Customer Care" : "Sign in to send"}</button>
          </div>
          <div className="space-y-2">
            <div className="font-medium text-sm flex items-center gap-2"><Phone size={15} /> Talk to our voice assistant</div>
            <div className="muted text-sm">11 Indian languages. The assistant knows your open claims and orders (same record as this page), can check coverage, register products, take claim details and place orders during the call — approvals are always by a person.</div>
            <div className="flex gap-2 flex-wrap">
              {voice.phone_number && <a className="btn primary inline-flex items-center gap-2" href={`tel:${voice.phone_number}`}><PhoneCall size={15} /> Call {voice.phone_number}</a>}
              <button className="btn" onClick={callMe} disabled={busy}>{voice.outbound_ready ? "Call me now" : "Request a call-back"}</button>
            </div>
            <div className="muted text-xs">Dial with the +91 prefix. Or we call you within a minute{session ? ` on ${session.phone}` : " (sign in first)"}.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
