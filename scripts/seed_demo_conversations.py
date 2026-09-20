"""Pre-run the demo conversations so the recording can show finished answers (with badges, conflicts and sources).

Sessions are the deterministic ids the UI opens by default:
  demo-internal-<employee id>   (internal chat, per signed-in team member)
  demo-customer-<phone>         (customer chat, per signed-in customer)   demo-customer-guest (not signed in)

    python scripts/seed_demo_conversations.py            # run everything
    python scripts/seed_demo_conversations.py --only harsh
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

BASE = "http://localhost:8010"
PW = "1234"


def _post(path: str, body: dict, headers: dict | None = None, stream: bool = False):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    r = urllib.request.urlopen(req, timeout=900)
    if not stream:
        return json.load(r)
    final = None
    buf = ""
    for line in r:
        line = line.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("event:"):
            buf = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and buf == "final":
            final = json.loads(line[5:].strip())
    return final


def chat(session: str, persona: str, msg: str, headers: dict | None = None):
    t = time.time()
    d = _post("/chat", {"session_id": session, "persona": persona, "message": msg}, headers, stream=True)
    if not d:
        print(f"   !! no final for: {msg[:60]}")
        return
    ir, out = d["ir"], d["output"]
    print(f"   {time.time() - t:5.0f}s  {ir['routing']['llm_used'] if ir.get('routing') else '-':6} {out['format']:7} conf={[c['verdict'] for c in ir['conflicts']]}  «{msg[:58]}»")


def customer_token(phone: str) -> dict:
    d = _post("/actions/login", {"phone": phone, "password": PW})
    return {"X-Customer-Token": d["token"]}


def team_token(emp: str) -> dict:
    d = _post("/actions/team/login", {"employee_id": emp, "password": PW})
    return {"X-Employee-Token": d["token"]}


INTERNAL = [
    "What is our paternity leave entitlement?",
    "Give me that as JSON",
    "Now make an Excel summary",
    "Draft an email to my manager requesting the leave",
    "Can I claim a ₹20,000 client dinner and does it comply with anti-bribery policy?",
    "A customer's intelligent toilet electronics failed after 4 years — is it covered? Draft the reply.",
    "Does Kohler still require ISO/TS 16949 from suppliers?",
    "Is our India privacy policy DPDP-ready?",
    "What's the FY26 salary band for a Grade 7 in Pune?",
]
HARSH = [
    "What is the warranty on a Kohler intelligent toilet in India?",
    "Compare water use of Cimarron, Highline and Wellworth in litres and show yearly savings for a family of four",
    "How do I cancel a kohler.co.in order and how is the refund paid?",
    "What is the status of my warranty claim and what do I still need to send?",
    "What's the FY26 salary band for a Grade 7 in Pune?",
]
VAIDEHI = [
    "Is my new Highline toilet registered for warranty, and what do I need to do?",
    "How much water does the Highline toilet use per flush compared to the Cimarron?",
    "What does the warranty cover on a Simplice kitchen faucet?",
]
GUEST = [
    "What is the warranty on a Kohler intelligent toilet in India?",
    "What personal data do you keep about me and how do I raise a grievance?",
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["internal", "harsh", "vaidehi", "guest"], nargs="*")
    ap.add_argument("--employees", nargs="*", default=["E001"])
    ap.add_argument("--reset", action="store_true", help="clear the target sessions first")
    a = ap.parse_args()
    only = set(a.only or ["internal", "harsh", "vaidehi", "guest"])

    def reset(sess):
        if a.reset:
            _post(f"/session/reset?session_id={sess}", {})

    if "internal" in only:
        for emp in a.employees:
            sess = f"demo-internal-{emp}"
            reset(sess)
            print(f"== internal chat as {emp} → {sess}")
            h = team_token(emp)
            for q in INTERNAL:
                chat(sess, "internal", q, h)
    if "harsh" in only:
        sess = "demo-customer-7093523468"; reset(sess)
        print(f"== customer chat as Harsh → {sess}")
        h = customer_token("7093523468")
        for q in HARSH:
            chat(sess, "customer", q, h)
    if "vaidehi" in only:
        sess = "demo-customer-9860231200"; reset(sess)
        print(f"== customer chat as Vaidehi → {sess}")
        h = customer_token("9860231200")
        for q in VAIDEHI:
            chat(sess, "customer", q, h)
    if "guest" in only:
        sess = "demo-customer-guest"; reset(sess)
        print(f"== guest chat → {sess}")
        for q in GUEST:
            chat(sess, "customer", q)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
