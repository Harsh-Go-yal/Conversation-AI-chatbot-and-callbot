import { useEffect, useState } from "react";
import { Moon, Sun, Monitor, Building2, User, MessageSquare, LifeBuoy, Ticket } from "lucide-react";
import Chat from "./components/Chat";
import HelpPanel from "./components/HelpPanel";
import Login from "./components/Login";
import TeamLogin from "./components/TeamLogin";
import InboxView from "./components/Inbox";
import { getSession, getTeamSession, onSessionChange, setSession, setTeamSession } from "./auth";
import { post } from "./api";
import type { Persona } from "./api";

type Theme = "light" | "dark" | "system";
type Tab = "chat" | "help" | "tickets";

function applyTheme(t: Theme) {
  const dark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export default function App() {
  const [persona, setPersona] = useState<Persona | null>(null);  // demo: every visit starts on the two-option landing page
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("theme") as Theme) || "system");
  const [session, setSess] = useState(getSession());
  const [team, setTeam] = useState(getTeamSession());
  const [showLogin, setShowLogin] = useState(false);
  const [showTeamLogin, setShowTeamLogin] = useState(false);
  useEffect(() => onSessionChange(() => { setSess(getSession()); setTeam(getTeamSession()); }), []);
  const [pendingTeamEntry, setPendingTeamEntry] = useState(false);
  useEffect(() => { if (pendingTeamEntry && getTeamSession()) { setPendingTeamEntry(false); setPersona("internal"); setTab("tickets"); } }, [team, pendingTeamEntry]);
  useEffect(() => { const h = () => setShowLogin(true); window.addEventListener("kohler:login", h); return () => window.removeEventListener("kohler:login", h); }, []);
  useEffect(() => { const h = () => setShowTeamLogin(true); window.addEventListener("kohler:team-login", h); return () => window.removeEventListener("kohler:team-login", h); }, []);
  const logout = async () => { await post("/actions/logout", {}); setSession(null); };
  const teamLogout = () => setTeamSession(null);
  const [tab, setTab] = useState<Tab>("chat");
  useEffect(() => { applyTheme(theme); localStorage.setItem("theme", theme); }, [theme]);

  const cycleTheme = () => setTheme(theme === "light" ? "dark" : theme === "dark" ? "system" : "light");
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  if (!persona) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="panel p-8 max-w-2xl w-full">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-xl font-medium">Kohler Assist</div>
              <div className="muted text-sm">Unified enterprise AI agent · Kohler India · prototype</div>
            </div>
            <button className="btn" onClick={cycleTheme} title={`Theme: ${theme}`}><ThemeIcon size={16} /></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button className="panel p-5 text-left hover:opacity-90" onClick={() => { setPersona("customer"); setTab("chat"); }}>
              <User size={22} className="mb-2" />
              <div className="font-medium">View as customer</div>
              <div className="muted text-sm mt-1">Ask about warranties, products, orders and water savings — no sign-in needed. Sign in with a mobile number to register products, raise claims, upload photos or talk to the voice assistant.</div>
              <div className="text-xs mt-3" style={{ color: "var(--accent)" }}>Enter →</div>
            </button>
            <button className="panel p-5 text-left hover:opacity-90" onClick={() => { if (getTeamSession()) { setPersona("internal"); setTab("tickets"); } else { setPendingTeamEntry(true); setShowTeamLogin(true); } }}>
              <Building2 size={22} className="mb-2" />
              <div className="font-medium">Login as internal team</div>
              <div className="muted text-sm mt-1">Ticket queue, claims decisions, call transcripts and the internal knowledge assistant (HR, finance, legal, support). Restricted content stays on the self-hosted model.</div>
              <div className="text-xs mt-3" style={{ color: "var(--accent)" }}>Sign in →</div>
            </button>
          </div>
          <div className="muted text-xs mt-4">Demo identities (fictional): customers <span className="mono">7093523468</span> (Harsh Goyal), <span className="mono">9860231200</span> (Vaidehi Bhangdia), <span className="mono">9810000101</span> (Rohan Mehta); team members Priya, Arjun, Meera, Rahul, Kavya — password <span className="mono">1234</span>. Voice line <span className="mono">+91 79658 53481</span>.</div>
          {showTeamLogin && <TeamLogin onClose={() => { setShowTeamLogin(false); setPendingTeamEntry(false); }} />}
          <div className="muted text-xs mt-6">This prototype is for educational and personal use only. All data in it is fictional — no real customer, order or company data — and nothing entered here is shared with anyone.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <header className="flex items-center gap-3 px-4 py-2 border-b" style={{ borderColor: "var(--border)", background: "var(--panel)" }}>
        <span className="font-medium">Kohler Assist</span>
        <span className="chip">{persona === "customer" ? "Customer" : "Internal team"}</span>
        <span className="muted text-xs">Region: India</span>
        <nav className="flex ml-4">
          <div className={`tab ${tab === "chat" ? "on" : ""}`} onClick={() => setTab("chat")}><MessageSquare size={13} className="inline mr-1" />Chat</div>
          {persona === "customer" && <div className={`tab ${tab === "help" ? "on" : ""}`} onClick={() => setTab("help")}><LifeBuoy size={13} className="inline mr-1" />Help with my product</div>}
          {persona === "internal" && <div className={`tab ${tab === "tickets" ? "on" : ""}`} onClick={() => setTab("tickets")}><Ticket size={13} className="inline mr-1" />Tickets</div>}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {persona === "internal" ? (team
            ? <><span className="muted text-xs">{team.name} · {team.role}</span><button className="btn small" onClick={teamLogout}>Sign out</button></>
            : <button className="btn small" onClick={() => setShowTeamLogin(true)}>Team sign-in</button>) : session
            ? <><span className="muted text-xs">{session.name || session.phone}</span><button className="btn small" onClick={logout}>Sign out</button></>
            : <button className="btn small" onClick={() => setShowLogin(true)}>Sign in</button>}
          <button className="btn small" onClick={cycleTheme} title={`Theme: ${theme}`}><ThemeIcon size={14} /></button>
          <button className="btn small" onClick={() => setPersona(null)}>Switch mode</button>
        </div>
      </header>
      {showLogin && <Login onClose={() => setShowLogin(false)} />}
      {showTeamLogin && <TeamLogin onClose={() => setShowTeamLogin(false)} />}
      <main className="flex-1 min-h-0">
        {tab === "chat" && <Chat persona={persona} key={persona + (session?.phone || "") + (team?.id || "")} />}
        {tab === "help" && <HelpPanel />}
        {tab === "tickets" && <InboxView key={team?.id || "none"} />}
      </main>
    </div>
  );
}
