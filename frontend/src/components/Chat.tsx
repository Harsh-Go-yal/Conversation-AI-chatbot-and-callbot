import { useEffect, useRef, useState } from "react";
import { Cloud, Lock, Send, Download, FileJson, FileSpreadsheet, FileCode2, Table2, Mail, AlertTriangle, Info, ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { chatStream, convert, downloadUrl, get, post, type Fmt, type IR, type Output, type Persona, type StageEvent } from "../api";
import { getSession, getTeamSession } from "../auth";

interface Turn { role: "user" | "assistant"; text: string; ir?: IR; output?: Output; stages?: StageEvent[]; error?: string; }

const SUGGEST: Record<Persona, string[]> = {
  customer: [
    "What is the warranty on a Kohler intelligent toilet in India?",
    "Compare water use of Cimarron, Highline and Wellworth in litres and show yearly savings for a family of four",
    "How do I cancel a kohler.co.in order and how is the refund paid?",
    "What personal data do you keep about me and how do I raise a grievance?",
  ],
  internal: [
    "What is our paternity leave entitlement?",
    "Can I claim a ₹20,000 client dinner and does it comply with anti-bribery policy?",
    "A customer's intelligent toilet electronics failed after 4 years — is it covered? Draft the reply.",
    "What's the FY26 salary band for a Grade 7 in Pune?",
    "Does Kohler still require ISO/TS 16949 from suppliers?",
  ],
};
const STAGES = ["router", "retrieval", "gate", "reasoner", "compiler"];
const FMT: { f: Fmt; label: string; icon: React.ReactNode }[] = [
  { f: "text", label: "Text", icon: null },
  { f: "json", label: "JSON", icon: <FileJson size={13} /> },
  { f: "excel", label: "Excel", icon: <FileSpreadsheet size={13} /> },
  { f: "xml", label: "XML", icon: <FileCode2 size={13} /> },
  { f: "markdown_table", label: "Table", icon: <Table2 size={13} /> },
  { f: "email", label: "Email", icon: <Mail size={13} /> },
];

export default function Chat({ persona }: { persona: Persona }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessKey = `session-${persona}-${persona === "customer" ? (getSession()?.phone || "guest") : (getTeamSession()?.id || "team")}`;
  // default conversation per identity (restored across reloads/restarts); "New" switches to a fresh random session
  const defaultSession = `demo-${persona}-${persona === "customer" ? (getSession()?.phone || "guest") : (getTeamSession()?.id || "team")}`;
  const [session, setSession] = useState<string | undefined>(() => localStorage.getItem(sessKey) || defaultSession);
  const [restoring, setRestoring] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [schema, setSchema] = useState("");
  const [showSchema, setShowSchema] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [debug, setDebug] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns]);
  useEffect(() => { if (session) localStorage.setItem(sessKey, session); }, [session, sessKey]);
  // restore the conversation (turns, pipeline stages, outputs, sources) after a reload or a backend restart
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    setRestoring(true);
    const apply = (d: { turns: Turn[] }) => {
      const ts = (d.turns || []).map((t) => ({ ...t, text: t.text || t.output?.content || t.ir?.summary || "" })) as Turn[];
      setTurns(ts);
      const last = [...ts].reverse().findIndex((t) => t.role === "assistant" && t.ir);
      if (last >= 0) setSelected(ts.length - 1 - last);
      return ts.length;
    };
    get<{ turns: Turn[] }>(`/session/${session}/turns`).then(async (d) => {
      if (cancelled) return;
      // a remembered session that is empty (e.g. an old random id) falls back to this identity's default conversation
      if (apply(d) === 0 && session !== defaultSession) {
        const d2 = await get<{ turns: Turn[] }>(`/session/${defaultSession}/turns`);
        if (!cancelled && (d2.turns || []).length) { setSession(defaultSession); apply(d2); }
      }
    }).catch(() => {}).finally(() => { if (!cancelled) setRestoring(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = selected !== null ? turns[selected] : [...turns].reverse().find((t) => t.ir);

  async function send(msg: string) {
    if (!msg.trim() || busy) return;
    setInput(""); setBusy(true);
    const idx = turns.length + 1;
    setTurns((t) => [...t, { role: "user", text: msg }, { role: "assistant", text: "", stages: [] }]);
    setSelected(null);
    try {
      let js: unknown = undefined;
      if (schema.trim()) { try { js = JSON.parse(schema); } catch { js = schema; } }
      for await (const ev of chatStream({ session_id: session, persona, message: msg, json_schema: js })) {
        if (ev.event === "session") setSession(ev.data.session_id as string);
        else if (ev.event === "stage") setTurns((t) => t.map((x, i) => (i === idx ? { ...x, stages: [...(x.stages || []), ev.data as StageEvent] } : x)));
        else if (ev.event === "final") {
          const d = ev.data as { ir: IR; output: Output };
          setTurns((t) => t.map((x, i) => (i === idx ? { ...x, ir: d.ir, output: d.output, text: d.output.content || d.ir.summary } : x)));
        } else if (ev.event === "error") setTurns((t) => t.map((x, i) => (i === idx ? { ...x, error: ev.data.message as string } : x)));
      }
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === idx ? { ...x, error: String(e) } : x)));
    } finally { setBusy(false); }
  }

  async function reformat(i: number, f: Fmt) {
    if (!session) return;
    setBusy(true);
    try {
      let js: unknown = undefined;
      if (f === "json" && schema.trim()) { try { js = JSON.parse(schema); } catch { js = schema; } }
      const r = await convert(session, f, js, f === "email" ? recipient || undefined : undefined);
      setTurns((t) => t.map((x, k) => (k === i ? { ...x, output: r.output, text: r.output.content || x.text } : x)));
    } catch (e) { alert(String(e)); } finally { setBusy(false); }
  }

  function reset() { if (session) post(`/session/reset?session_id=${session}`, {}).catch(() => {}); setTurns([]); setSession(undefined); setSelected(null); localStorage.removeItem(sessKey); }

  return (
    <div className="h-full grid" style={{ gridTemplateColumns: "minmax(0,1.7fr) minmax(300px,1fr)" }}>
      <section className="flex flex-col min-h-0 border-r" style={{ borderColor: "var(--border)" }}>
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {restoring && turns.length === 0 && <div className="muted text-sm p-4">Restoring your conversation…</div>}
          {turns.length === 0 && !restoring && (
            <div className="max-w-2xl mx-auto mt-10">
              <div className="text-lg font-medium mb-1">{persona === "customer" ? "How can we help?" : "Ask the knowledge base"}</div>
              <div className="muted text-sm mb-4">{persona === "customer" ? "Warranties, products, orders, water savings and privacy — answered from Kohler India's published documents." : "HR, finance, legal, privacy, support and sustainability. Answers are cited; restricted content is reasoned over on-device."}</div>
              <div className="grid gap-2">{SUGGEST[persona].map((s) => <button key={s} className="btn text-left" onClick={() => send(s)}>{s}</button>)}</div>
            </div>
          )}
          {turns.map((t, i) => t.role === "user" ? (
            <div key={i} className="flex justify-end"><div className="rounded-2xl px-4 py-2 max-w-[85%]" style={{ background: "var(--panel-2)" }}>{t.text}</div></div>
          ) : (
            <div key={i} className={`space-y-2 ${selected === i ? "" : ""}`} onClick={() => setSelected(i)}>
              {persona === "internal" && t.stages && t.stages.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {STAGES.map((s) => { const ev = t.stages!.find((e) => e.stage === s); const active = !ev && !t.ir && !t.error && t.stages!.length && STAGES.indexOf(s) === t.stages!.filter(e => STAGES.includes(e.stage)).length; return (
                    <span key={s} className={`chip ${ev ? "done" : active ? "active" : ""}`}>{ev ? "✓" : active ? "…" : "·"} {s}{ev && typeof ev.ms === "number" ? ` ${((ev.ms as number) / 1000).toFixed(1)}s` : ""}{s === "retrieval" && ev ? ` · ${ev.n} chunks` : ""}{s === "gate" && ev ? ` · ${(ev.restricted_chunks as number) > 0 ? "restricted" : "public/internal"}` : ""}</span>); })}
                  {t.stages.find((e) => e.stage === "reuse") && <span className="chip done"><RefreshCw size={11} /> reused previous answer</span>}
                </div>
              )}
              {t.ir?.routing && persona === "internal" && (
                <div className={`banner ${t.ir.routing.llm_used === "local" ? "lock" : "info"} inline-flex items-center gap-2`}>
                  {t.ir.routing.llm_used === "local" ? <Lock size={14} /> : <Cloud size={14} />}
                  {t.ir.routing.llm_used === "local" ? "On-device model" : "Cloud model"} · {t.ir.routing.model} · {t.ir.routing.reason}
                </div>
              )}
              {t.ir?.conflicts?.map((c, k) => (
                <div key={k} className="banner warn"><AlertTriangle size={14} className="inline mr-1" /><b>{c.verdict === "superseded" ? "Superseded version" : c.verdict === "review_recommended" ? "Review recommended" : "Conflicting documents"}.</b> {c.reason} {c.resolution}</div>
              ))}
              {t.ir?.access_notes?.map((n, k) => <div key={k} className="banner info"><Info size={14} className="inline mr-1" />{n.message}</div>)}
              {t.error && <div className="banner lock">Error: {t.error}</div>}
              {!t.ir && !t.error && <div className="muted text-sm">Thinking…</div>}
              {t.ir && <AnswerBody turn={t} onCite={() => setSelected(i)} />}
              {t.ir && (
                <div className="flex flex-wrap items-center gap-1 pt-1">
                  <span className="muted text-xs mr-1">Show as</span>
                  {FMT.filter((x) => persona === "internal" || ["text", "markdown_table", "excel", "email"].includes(x.f)).map((x) => (
                    <button key={x.f} className={`btn small ${t.output?.format === x.f ? "primary" : ""}`} disabled={busy} onClick={(e) => { e.stopPropagation(); if (x.f === "json") setShowSchema(true); reformat(i, x.f); }}>{x.icon} {x.label}</button>
                  ))}
                  {t.output?.download_id && <a className="btn small" href={downloadUrl(t.output.download_id)}><Download size={13} /> {t.output.filename}</a>}
                </div>
              )}
              {t.output?.action_hint && persona === "customer" && <div className="banner info">Use the “Help with my product” tab above to register, claim or order. <button className="btn small ml-2" onClick={() => window.dispatchEvent(new Event("kohler:login"))}>Sign in</button> with your mobile number and I will pick up where we left off — on the website or on the phone.</div>}
            </div>
          ))}
          <div ref={bottom} />
        </div>
        {showSchema && persona === "internal" && (
          <div className="px-4 pb-2">
            <div className="flex items-center gap-2 text-xs muted mb-1"><span>JSON schema (optional) — paste a schema and re-click JSON</span><button className="btn small" onClick={() => setShowSchema(false)}>hide</button></div>
            <textarea className="input mono" rows={4} value={schema} onChange={(e) => setSchema(e.target.value)} placeholder='{"type":"object","properties":{"entitlement_days":{"type":"integer"},"policy_version":{"type":"string"}},"required":["entitlement_days"]}' />
          </div>
        )}
        <div className="p-3 border-t flex gap-2 items-center" style={{ borderColor: "var(--border)" }}>
          <input className="input" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send(input)} placeholder={persona === "customer" ? "Ask about warranties, products, orders…" : "Ask about policies, warranties, products…"} disabled={busy} />
          {persona === "internal" && <input className="input" style={{ width: 180 }} value={recipient} onChange={(e) => setRecipient(e.target.value)} placeholder="Email to… (optional)" />}
          <button className="btn primary" onClick={() => send(input)} disabled={busy}><Send size={15} /></button>
          <button className="btn" onClick={reset} title="New conversation">New</button>
        </div>
      </section>
      <aside className="min-h-0 overflow-auto p-4" style={{ background: "var(--panel-2)" }}>
        <SourcesPanel ir={current?.ir} persona={persona} />
        {persona === "internal" && current?.ir && (
          <div className="mt-4">
            <button className="btn small" onClick={() => setDebug(!debug)}>{debug ? <ChevronDown size={12} /> : <ChevronRight size={12} />} Pipeline details (AnswerIR)</button>
            {debug && <pre className="code mt-2">{JSON.stringify(current.ir, null, 1)}</pre>}
          </div>
        )}
      </aside>
    </div>
  );
}

function AnswerBody({ turn, onCite }: { turn: Turn; onCite: () => void }) {
  const o = turn.output;
  if (!o) return null;
  if (o.format === "email") return (
    <div className="panel p-3 text-sm" onClick={onCite}>
      <div className="muted text-xs mb-1">Draft email{o.to ? ` · to: ${o.to}` : ""}</div>
      <div className="font-medium mb-2">Subject: {o.subject}</div>
      <pre className="whitespace-pre-wrap font-sans text-sm">{o.body}</pre>
      {o.citations && o.citations.length > 0 && <div className="muted text-xs mt-2">Based on: {o.citations.join(" · ")}</div>}
      <div className="mt-2"><button className="btn small" onClick={() => navigator.clipboard.writeText(`Subject: ${o.subject}\n\n${o.body}`)}>Copy</button></div>
    </div>
  );
  if (o.format === "json" || o.format === "xml") return (
    <div>
      {o.validation && <div className={`banner ${o.validation.validated ? "info" : "lock"} mb-2 text-xs`}>{o.validation.validated ? `Validated against ${o.validation.schema === "user" ? "your schema" : "the default schema"}` : `Validation failed: ${o.validation.error}`}{o.validation.attempts > 1 ? ` (after ${o.validation.attempts} attempts)` : ""}</div>}
      <pre className="code">{o.content}</pre>
    </div>
  );
  if (o.format === "markdown_table") return <pre className="code whitespace-pre-wrap">{o.content}</pre>;
  if (o.format === "excel") return <div className="banner info">Excel workbook generated — Answer, Claims, Sources{turn.ir?.conflicts?.length ? ", Version notes" : ""} sheets{/litre|gpf|lpf/i.test(turn.ir?.summary || "") ? " and a live Water-savings calculator" : ""}. Use the download button.</div>;
  const body = (o.content || turn.ir?.summary || "").split("\n").filter((l) => !/^[⚠ℹ]/.test(l.trim())).join("\n").replace(/\n{3,}/g, "\n\n").trim();
  return <div className="text-[15px] leading-relaxed whitespace-pre-wrap" onClick={onCite}>{renderCites(body)}</div>;
}

function renderCites(text: string) {
  const parts = text.split(/(\[s\d+\])/g);
  return parts.map((p, i) => (/^\[s\d+\]$/.test(p) ? <span key={i} className="cite">{p}</span> : <span key={i}>{p}</span>));
}

function SourcesPanel({ ir, persona }: { ir?: IR; persona: Persona }) {
  if (!ir) return <div className="muted text-sm">Sources for the selected answer appear here.</div>;
  return (
    <div>
      <div className="font-medium mb-2 text-sm">Sources ({ir.sources.length})</div>
      {ir.sources.map((s) => {
        const superseded = ir.conflicts.some((c) => c.verdict === "superseded" && c.source_a === s.id);
        return (
          <div key={s.id} className="panel p-2 mb-2 text-xs" style={superseded ? { opacity: 0.7 } : {}}>
            <div><span className="cite">[{s.id}]</span> <b>{s.title}</b>{s.version ? ` · v${s.version}` : ""}{s.page ? ` · p.${s.page}` : ""}{persona === "internal" ? ` · ${s.origin === "synthetic" ? "fictional" : "original"}` : ""}{superseded ? " · superseded" : ""}{s.sensitivity === "restricted" ? <Lock size={11} className="inline ml-1" /> : null}</div>
            {s.section && <div className="muted">{s.section}{s.effective_date ? ` · effective ${s.effective_date}` : ""}</div>}
            <div className="mt-1 muted">“{s.excerpt}”</div>
          </div>
        );
      })}
      {Object.entries(ir.entities || {}).filter(([, v]) => v && v.length).length > 0 && (
        <div className="mt-3 text-xs">
          <div className="font-medium mb-1">Extracted</div>
          {Object.entries(ir.entities).filter(([, v]) => v && v.length).map(([k, v]) => <div key={k}><span className="muted">{k}:</span> {v.join(", ")}</div>)}
        </div>
      )}
    </div>
  );
}
