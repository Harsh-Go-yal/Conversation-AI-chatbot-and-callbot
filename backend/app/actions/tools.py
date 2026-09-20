"""Guarded action tools. Each returns a dict with `ok`, a human `message`, and a `rule` string explaining which
policy rule was applied. Used by the chat UI panel, the REST API and the Sarvam voice agent (via API tools)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime

from app.actions import crm
from app.config import settings
from app.actions.crm import TIER1_PART_LIMIT_INR, WARRANTY_YEARS

IN12B = "Kohler India Warranty Policy 1677778-IN12-B"
ESCALATION = "Customer Care Escalation Matrix v3.4 (Tier 1 authority ≤ ₹5,000 replacement parts)"


def lookup_order(order_no: str | None = None, phone: str | None = None, channel: str = "chat", actor: str = "customer") -> dict:
    if order_no:
        orders = crm.rows("SELECT o.*, c.name, c.phone, c.email FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.order_no=?", order_no.strip().upper())
    elif phone:
        p = "".join(ch for ch in phone if ch.isdigit())[-10:]
        orders = crm.rows("SELECT o.*, c.name, c.phone, c.email FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.phone LIKE ? ORDER BY o.order_date DESC", f"%{p}")
    else:
        return {"ok": False, "message": "Provide an order number or a phone number."}
    for o in orders:
        o["items"] = crm.rows("SELECT i.sku, i.qty, p.name, p.category, p.price_inr, (SELECT COUNT(*) FROM registrations r WHERE r.order_no=i.order_no AND r.sku=i.sku) AS registered FROM order_items i JOIN products p ON p.sku=i.sku WHERE i.order_no=?", o["order_no"])
    res = {"ok": bool(orders), "orders": orders, "message": (f"Found {len(orders)} order(s)." if orders else "No order found for those details.")}
    crm.audit(channel, actor, "lookup_order", {"order_no": order_no, "phone": phone}, {"found": len(orders)}, "read-only", "")
    return res


def register_warranty(order_no: str, sku: str, channel: str = "chat", actor: str = "customer") -> dict:
    o = crm.rows("SELECT * FROM orders WHERE order_no=?", order_no)
    if not o:
        return {"ok": False, "message": f"Order {order_no} not found."}
    item = crm.rows("SELECT * FROM order_items WHERE order_no=? AND sku=?", order_no, sku)
    if not item:
        return {"ok": False, "message": f"{sku} is not on order {order_no}."}
    if crm.rows("SELECT 1 FROM registrations WHERE order_no=? AND sku=?", order_no, sku):
        res = {"ok": True, "message": f"{sku} on order {order_no} is already registered.", "rule": "already registered"}
    else:
        c = crm.conn(); c.execute("INSERT INTO registrations(order_no, sku, registered_on, channel) VALUES (?,?,?,?)", (order_no, sku, date.today().isoformat(), channel)); c.commit(); c.close()
        res = {"ok": True, "message": f"Registered {sku} on order {order_no}. Warranty runs from the purchase date {o[0]['order_date']}.", "rule": f"{IN12B}: product must be registered on the portal to claim"}
    crm.audit(channel, actor, "register_warranty", {"order_no": order_no, "sku": sku}, res, res.get("rule", ""), IN12B)
    return res


def check_warranty(order_no: str, sku: str, issue: str = "", channel: str = "chat", actor: str = "customer") -> dict:
    o = crm.rows("SELECT o.*, p.category, p.name FROM orders o JOIN order_items i ON i.order_no=o.order_no JOIN products p ON p.sku=i.sku WHERE o.order_no=? AND i.sku=?", order_no, sku)
    if not o:
        return {"ok": False, "message": f"{sku} on order {order_no} not found."}
    o = o[0]
    years = WARRANTY_YEARS.get(o["category"], 2)
    purchased = date.fromisoformat(o["order_date"])
    age_days = (date.today() - purchased).days
    expires = purchased.replace(year=purchased.year + years)
    registered = bool(crm.rows("SELECT 1 FROM registrations WHERE order_no=? AND sku=?", order_no, sku))
    covered = date.today() <= expires
    part_note = ""
    if o["category"] == "intelligent_toilet":
        part_note = " Ceramic body is covered 10 years; mechanical/electronic components 5 years with preventive maintenance (IN12-B; the superseded IN12-A stated 3 years)."
    res = {"ok": True, "covered": covered, "registered": registered, "category": o["category"], "product": o["name"],
           "purchased": o["order_date"], "warranty_years": years, "expires": expires.isoformat(), "age_days": age_days,
           "message": (f"{o['name']} purchased {o['order_date']}: {'within' if covered else 'outside'} the {years}-year residential warranty (expires {expires.isoformat()})."
                       + ("" if registered else " The product is not yet registered — registration is required before a claim.") + part_note),
           "rule": f"{IN12B}: {o['category']} residential coverage {years} years from purchase; registration required"}
    crm.audit(channel, actor, "check_warranty", {"order_no": order_no, "sku": sku, "issue": issue}, res, res["rule"], IN12B)
    return res


INTAKE_FIELDS = [  # what a complete warranty claim needs before a person can decide it
    ("problem", "what exactly is wrong"),
    ("since_when", "when the problem started"),
    ("symptoms", "constant or intermittent; any error lights, noise or leakage"),
    ("installed_by", "who installed it (Kohler-authorised installer or other) and when"),
    ("usage", "residential or commercial use"),
    ("preferred_slot", "preferred day/time for a service visit"),
    ("contact_phone", "a phone number for the service team"),
]


def _parse_intake(issue: str, details: dict | None) -> dict:
    """Voice/chat may pack the intake into one text: 'Problem: …; Since: …; Symptoms: …'. Split labelled segments."""
    out = {k: v for k, v in (details or {}).items() if v}
    labels = {"problem": "problem", "issue": "problem", "since": "since_when", "since when": "since_when", "started": "since_when",
              "symptoms": "symptoms", "symptom": "symptoms", "installed by": "installed_by", "installer": "installed_by", "installation": "installed_by",
              "usage": "usage", "use": "usage", "preferred slot": "preferred_slot", "slot": "preferred_slot", "visit": "preferred_slot",
              "contact": "contact_phone", "phone": "contact_phone", "contact phone": "contact_phone"}
    for seg in re.split(r"[;\n]+", issue or ""):
        if ":" in seg:
            k, v = seg.split(":", 1)
            key = labels.get(k.strip().lower())
            if key and v.strip():
                out.setdefault(key, v.strip())
    if "problem" not in out and issue:
        out["problem"] = issue.strip()[:300]
    return out


def open_claim(order_no: str, sku: str, issue: str, estimated_cost_inr: int | None = None, channel: str = "chat", actor: str = "customer",
               details: dict | None = None, contact_phone: str = "") -> dict:
    """Register a warranty claim for HUMAN decision. The system never approves or declines — it checks coverage, records
    the intake, computes a recommendation from the policy rules and routes the claim to the Customer Care inbox."""
    w = check_warranty(order_no, sku, issue, channel, actor)
    if not w.get("ok"):
        return w
    if not w["registered"]:
        register_warranty(order_no, sku, channel, actor)  # allowed by policy when proof of purchase (the order) exists
    intake = _parse_intake(issue, details)
    if contact_phone:
        intake["contact_phone"] = contact_phone
    missing = [label for key, label in INTAKE_FIELDS if not intake.get(key)]
    cost = estimated_cost_inr if estimated_cost_inr is not None else (2500 if w["category"] in ("faucet", "faucet_fitting", "accessory", "showerhead") else 8000)
    cid = "CLM-" + uuid.uuid4().hex[:6].upper()
    token = uuid.uuid4().hex[:12]
    if not w["covered"]:
        rec, rule = f"Outside warranty (expired {w['expires']}) — recommend paid service visit", f"{IN12B}: outside warranty period"
    elif cost <= TIER1_PART_LIMIT_INR:
        rec, rule = f"Within warranty; replacement part ≤ ₹{TIER1_PART_LIMIT_INR:,} — Tier-1 eligible, recommend approve", f"{ESCALATION}: Tier-1 limit ₹{TIER1_PART_LIMIT_INR:,}"
    else:
        rec, rule = f"Within warranty; estimated ₹{cost:,} exceeds Tier-1 authority — Tier-2 review", f"{ESCALATION}: above Tier-1 limit"
    rule += " · human approval required for every claim"
    upload_url = (settings.public_base_url.rstrip("/") if settings.public_base_url else "http://localhost:8010") + f"/claim-upload/{token}"
    c = crm.conn()
    c.execute("INSERT INTO claims(id, order_no, sku, issue, status, decision_rule, remedy, estimated_cost_inr, created_on, channel, details, photos, recommendation, upload_token, contact_phone) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (cid, order_no, sku, intake.get("problem", issue), "pending", rule, "Awaiting Customer Care decision", cost,
               datetime.utcnow().isoformat(timespec="seconds"), channel, json.dumps(intake), "[]", rec, token, intake.get("contact_phone", "")))
    c.commit(); c.close()
    res = {"ok": True, "claim_id": cid, "status": "pending", "remedy": "Awaiting Customer Care decision", "estimated_cost_inr": cost, "rule": rule,
           "recommendation": rec, "covered": w["covered"], "expires": w["expires"], "intake": intake, "missing_info": missing,
           "upload_url": upload_url,
           "message": (f"Claim {cid} registered and sent to Kohler Customer Care for review; a specialist will decide and confirm within 2 working days. "
                       f"Photos of the product and the fault can be uploaded at the link sent by SMS.")
                      + (f" Still needed for a faster decision: {', '.join(missing)}." if missing else " All intake details captured.")}
    crm.audit(channel, actor, "open_claim", {"order_no": order_no, "sku": sku, "issue": issue, "cost": cost, "intake": intake}, {k: res[k] for k in ("claim_id", "status", "recommendation")}, rule, f"{IN12B}; {ESCALATION}")
    body = (f"Order {order_no}, {sku}: {intake.get('problem', issue)}\nEstimated ₹{cost:,} · {rec}\n"
            + "\n".join(f"{k}: {v}" for k, v in intake.items() if k != "problem")
            + (f"\nMissing: {', '.join(missing)}" if missing else "") + f"\nPhotos: {upload_url}")
    phone = intake.get("contact_phone") or crm.rows("SELECT cu.phone FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE o.order_no=?", order_no)[0]["phone"]
    tid = create_ticket("claim_review", phone, f"Claim {cid}: {w['product']} — {intake.get('problem', issue)[:60]}", body, cid, order_no, channel,
                        priority="high" if not w["covered"] else "normal")
    res["ticket_id"] = tid
    notify_customer(phone, f"Claim {cid} registered",
                    f"Kohler India: your warranty claim {cid} for {w['product']} is registered and with Customer Care for review (decision within 2 working days). "
                    f"Please upload photos of the product and the fault here: {upload_url}"
                    + (f" We still need: {', '.join(missing)}." if missing else ""), cid, channel)
    remember(phone, channel, f"Registered claim {cid} for {w['product']}: {intake.get('problem', issue)[:80]}", _claim_open_items(phone))
    res["notified"] = phone
    return res


def add_claim_photos(claim_id: str, files: list[tuple[str, bytes]], token: str | None = None, channel: str = "web") -> dict:
    row = crm.rows("SELECT * FROM claims WHERE id=?", claim_id)
    if not row:
        return {"ok": False, "message": f"Claim {claim_id} not found."}
    if token is not None and token != row[0]["upload_token"]:
        return {"ok": False, "message": "Invalid upload link."}
    folder = crm.UPLOADS / claim_id
    folder.mkdir(parents=True, exist_ok=True)
    photos = json.loads(row[0]["photos"] or "[]")
    for name, data in files:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[-60:] or "photo"
        path = folder / f"{len(photos) + 1:02d}_{safe}"
        path.write_bytes(data[:8_000_000])
        photos.append(path.name)
    c = crm.conn(); c.execute("UPDATE claims SET photos=? WHERE id=?", (json.dumps(photos), claim_id)); c.commit(); c.close()
    crm.audit(channel, "customer", "add_claim_photos", {"claim_id": claim_id, "n": len(files)}, {"photos": len(photos)}, "always allowed", "")
    t = ticket_for_ref(claim_id)
    if t:
        ticket_event(t["id"], "customer", "photos", f"{len(files)} photo(s) received ({len(photos)} total) — ready for decision")
        set_ticket_status(t["id"], "open" if t["status"] in ("waiting_customer", "open") else t["status"], "system") if t["status"] == "waiting_customer" else None
    phone = row[0]["contact_phone"] or crm.rows("SELECT cu.phone FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE o.order_no=?", row[0]["order_no"])[0]["phone"]
    notify_customer(phone, f"Claim {claim_id}: photos received", f"Kohler India: we received {len(files)} photo(s) for claim {claim_id}. A Customer Care specialist will now review it and confirm within 2 working days.", claim_id, channel)
    remember(phone, channel, f"Uploaded {len(files)} photo(s) for claim {claim_id}", _claim_open_items(phone))
    return {"ok": True, "claim_id": claim_id, "photos": photos, "message": f"{len(files)} photo(s) attached to claim {claim_id}. Customer Care will now review it."}


def place_order(sku: str, qty: int, phone: str, address: str, channel: str = "chat", actor: str = "customer") -> dict:
    if not _norm_phone(phone):
        return {"ok": False, "message": "A mobile number is needed to place an order (for the payment link and delivery updates)."}
    p = crm.rows("SELECT * FROM products WHERE sku=?", sku)
    if not p:
        return {"ok": False, "message": f"{sku} is not in the catalog."}
    cust = crm.rows("SELECT * FROM customers WHERE phone LIKE ?", f"%{''.join(ch for ch in phone if ch.isdigit())[-10:]}")
    cid = cust[0]["id"] if cust else "C-NEW"
    order_no = "KI-" + date.today().strftime("%Y") + "-" + uuid.uuid4().hex[:4].upper()
    total = p[0]["price_inr"] * qty
    c = crm.conn()
    if not cust:
        c.execute("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?)", (cid, "New customer", phone, "", address))
    c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (order_no, cid, date.today().isoformat(), "awaiting_payment", channel, total, address))
    c.execute("INSERT INTO order_items VALUES (?,?,?)", (order_no, sku, qty))
    c.commit(); c.close()
    tid = create_ticket("order_help", phone, f"New order {order_no}: {qty} × {p[0]['name']}", f"Order placed via {channel}; payment link to be sent; confirm delivery address: {address}", order_no, order_no, channel)
    res = {"ok": True, "order_no": order_no, "ticket_id": tid, "total_inr": total, "status": "awaiting_payment",
           "message": f"Order {order_no} created for {qty} × {p[0]['name']} (₹{total:,}), awaiting payment. A payment link will be sent by SMS.",
           "rule": "Catalog SKU; orders are created as awaiting_payment until paid (Kohler India Terms of Service)"}
    crm.audit(channel, actor, "place_order", {"sku": sku, "qty": qty, "phone": phone}, res, res["rule"], "Kohler India Terms of Service")
    return res


def request_callback(phone: str, reason: str, channel: str = "chat", actor: str = "customer") -> dict:
    c = crm.conn()
    c.execute("INSERT INTO callbacks(phone, reason, status, created_on, channel) VALUES (?,?,?,?,?)", (phone, reason, "requested", datetime.utcnow().isoformat(timespec="seconds"), channel))
    c.commit(); c.close()
    tid = create_ticket("callback", phone, f"Call-back: {reason[:80]}", f"Customer asked to be called back. Reason: {reason}", "", None, channel)
    res = {"ok": True, "ticket_id": tid, "message": f"Call-back requested for {phone} (ticket {tid}). Customer Care hours: Mon–Sat 08:00–20:00.", "rule": "always allowed"}
    remember(phone, channel, f"Requested a call-back: {reason[:80]} ({tid})")
    crm.audit(channel, actor, "request_callback", {"phone": phone, "reason": reason}, res, "always allowed", "")
    return res


# ───────────────────────── customer memory, notifications, cross-channel context ─────────────────────────
def _norm_phone(phone: str | None) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())[-10:]


def remember(phone: str, channel: str, summary: str = "", open_items: list[str] | None = None, name: str = "", email: str = "") -> None:
    """One memory row per customer (keyed by mobile number) shared by chat and voice: who they are, what happened last,
    and what is still open — so the next conversation on either channel resumes where the last one ended."""
    ph = _norm_phone(phone)
    if not ph:
        return
    c = crm.conn()
    row = c.execute("SELECT * FROM customer_memory WHERE phone=?", (ph,)).fetchone()
    if not name:
        cust = c.execute("SELECT name, email FROM customers WHERE phone LIKE ?", (f"%{ph}",)).fetchone()
        name = (cust["name"] if cust else (row["name"] if row else "")) or ""
        email = email or (cust["email"] if cust else (row["email"] if row else "")) or ""
    items = open_items if open_items is not None else json.loads(row["open_items"]) if row and row["open_items"] else []
    c.execute("INSERT INTO customer_memory(phone, name, email, last_channel, last_summary, open_items, updated_on) VALUES (?,?,?,?,?,?,?) "
              "ON CONFLICT(phone) DO UPDATE SET name=excluded.name, email=excluded.email, last_channel=excluded.last_channel, "
              "last_summary=CASE WHEN excluded.last_summary='' THEN customer_memory.last_summary ELSE excluded.last_summary END, "
              "open_items=excluded.open_items, updated_on=excluded.updated_on",
              (ph, name, email, channel, summary or "", json.dumps(items), datetime.utcnow().isoformat(timespec="seconds")))
    c.commit(); c.close()


def notify_customer(phone: str, subject: str, body: str, ref: str = "", channel: str = "system", email: str = "") -> dict:
    """Follow-up to the customer after an action: recorded as an SMS and an email in the outbox (the prototype has no
    SMS/e-mail gateway — the internal Inbox and the customer's 'My messages' page show exactly what would be sent)."""
    ph = _norm_phone(phone)
    if not email and ph:
        cust = crm.rows("SELECT email FROM customers WHERE phone LIKE ?", f"%{ph}")
        email = cust[0]["email"] if cust else ""
    ids = []
    if ph:
        ids.append(_to_inbox("customer_sms", ph, f"SMS → {ph}: {subject}", body[:480], ref or None, channel))
    if email:
        ids.append(_to_inbox("customer_email", email, f"Email → {email}: {subject}", body, ref or None, channel))
    return {"sent": len(ids), "sms_to": ph, "email_to": email}


def _claim_open_items(phone: str) -> list[str]:
    ph = _norm_phone(phone)
    rows = crm.rows("SELECT c.* FROM claims c JOIN orders o ON o.order_no=c.order_no JOIN customers cu ON cu.id=o.customer_id "
                    "WHERE (cu.phone LIKE ? OR c.contact_phone LIKE ?) AND c.status='pending' ORDER BY c.created_on DESC", f"%{ph}", f"%{ph}")
    items = []
    for r in rows:
        photos = json.loads(r["photos"] or "[]")
        step = "waiting for the customer's photos" if not photos else "photos received — awaiting Customer Care decision"
        items.append(f"claim {r['id']} ({r['sku']}: {r['issue'][:60]}) — {step}")
    return items


def customer_context(phone: str) -> dict:
    """Everything an agent (voice or chat) needs to greet a returning customer and resume: name, orders, open claims
    with their next step, last interaction summary. Customer-facing — no internal recommendation is exposed."""
    ph = _norm_phone(phone)
    if not ph:
        return {"ok": False, "known": False, "summary": "", "message": "No phone number given."}
    mem = crm.rows("SELECT * FROM customer_memory WHERE phone=?", ph)
    cust = crm.rows("SELECT * FROM customers WHERE phone LIKE ?", f"%{ph}")
    name = (mem[0]["name"] if mem else "") or (cust[0]["name"] if cust else "")
    orders = crm.rows("SELECT o.order_no, o.order_date, o.status FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE cu.phone LIKE ? ORDER BY o.order_date DESC", f"%{ph}")
    claims = crm.rows("SELECT c.* FROM claims c JOIN orders o ON o.order_no=c.order_no JOIN customers cu ON cu.id=o.customer_id "
                      "WHERE (cu.phone LIKE ? OR c.contact_phone LIKE ?) ORDER BY c.created_on DESC LIMIT 5", f"%{ph}", f"%{ph}")
    claim_list = []
    for r in claims:
        photos = json.loads(r["photos"] or "[]")
        intake = json.loads(r["details"] or "{}")
        missing = [label for key, label in INTAKE_FIELDS if not intake.get(key)]
        if r["status"] == "pending":
            next_step = ("Please upload photos of the product and the fault (link sent by SMS / on the website)." if not photos
                         else "Photos received; a Customer Care specialist will decide within 2 working days.")
        elif r["status"] == "approved":
            next_step = "Approved — the service visit will be scheduled; the team will call to fix the slot."
        else:
            next_step = "Declined under warranty — a paid service visit can be booked."
        claim_list.append({"claim_id": r["id"], "order_no": r["order_no"], "sku": r["sku"], "issue": r["issue"], "status": r["status"],
                           "created_on": r["created_on"], "photos": len(photos), "missing_info": missing, "next_step": next_step,
                           "upload_url": (settings.public_base_url.rstrip("/") if settings.public_base_url else "http://localhost:8010") + f"/claim-upload/{r['upload_token']}",
                           "decision_note": r["decision_note"] or ""})
    callbacks = crm.rows("SELECT reason, status, created_on FROM callbacks WHERE phone LIKE ? ORDER BY id DESC LIMIT 3", f"%{ph}")
    tickets = list_tickets(None, None, None, ph)[:6]
    for t in tickets:
        last = crm.rows("SELECT ts, kind, text FROM ticket_events WHERE ticket_id=? AND kind IN ('reply','status') ORDER BY id DESC LIMIT 1", t["id"])
        t["last_update"] = last[0] if last else None
    known = bool(name or orders or claims or mem)
    last = mem[0]["last_summary"] if mem else ""
    open_items = json.loads(mem[0]["open_items"]) if mem and mem[0]["open_items"] else _claim_open_items(ph)
    # one paragraph the voice agent can read as context
    parts = []
    if name:
        parts.append(f"Returning customer: {name} ({ph}).")
    if last:
        parts.append(f"Last interaction ({mem[0]['last_channel']}, {mem[0]['updated_on'][:10]}): {last}")
    for cl in claim_list[:2]:
        parts.append(f"Claim {cl['claim_id']} for {cl['sku']} is {cl['status']}; next step: {cl['next_step']}")
    for t in tickets[:2]:
        if not (t["ref"] or "").startswith("CLM-"):
            upd = (t.get("last_update") or {}).get("text", "")
            parts.append(f"Ticket {t['id']} ({TICKET_KINDS.get(t['kind'], t['kind'])}: {t['subject'][:50]}) is {t['status'].replace('_', ' ')}" + (f"; team said: {upd[:100]}" if upd and t.get('last_update', {}).get('kind') == 'reply' else ""))
    if orders and not claim_list:
        parts.append("Orders: " + ", ".join(f"{o['order_no']} ({o['order_date']})" for o in orders[:3]))
    if not known:
        parts.append("New caller — no previous record for this number.")
    summary = " ".join(parts)
    crm.audit("system", "agent", "customer_context", {"phone": ph}, {"known": known, "claims": len(claim_list)}, "customer's own data only", "")
    return {"ok": True, "known": known, "phone": ph, "name": name, "orders": orders, "claims": claim_list, "callbacks": callbacks, "tickets": tickets,
            "last_summary": last, "open_items": open_items, "summary": summary,
            "message": summary}


def my_messages(phone: str) -> list[dict]:
    ph = _norm_phone(phone)
    if not ph:
        return []
    cust = crm.rows("SELECT email FROM customers WHERE phone LIKE ?", f"%{ph}")
    email = (cust[0]["email"] if cust else "") or "-"
    return crm.rows("SELECT id, kind, subject, body, created_on, channel, order_no FROM outbox WHERE kind IN ('customer_sms','customer_email') AND (to_addr LIKE ? OR to_addr=?) ORDER BY id DESC LIMIT 30", f"%{ph}%", email)


def follow_up_after_conversation(phone: str, channel: str, summary: str, actions: list[str] | None = None) -> dict:
    """Called at the end of a voice call (webhook) or when a chat session closes: store the memory and send the
    customer a recap of what was done and what happens next."""
    ph = _norm_phone(phone)
    if not ph:
        return {"ok": False, "message": "no phone"}
    items = _claim_open_items(ph)
    remember(ph, channel, summary, items)
    ctx = customer_context(ph)
    lines = [f"Namaste{(' ' + ctx['name']) if ctx.get('name') else ''}, thank you for contacting Kohler India Customer Care."]
    if summary:
        lines.append(f"Summary of your {('call' if channel == 'voice' else 'chat')}: {summary}")
    if actions:
        lines.append("Actions taken: " + "; ".join(actions))
    for cl in ctx["claims"][:2]:
        if cl["status"] == "pending":
            lines.append(f"Claim {cl['claim_id']} ({cl['sku']}): {cl['next_step']}" + (f" Upload link: {cl['upload_url']}" if cl["photos"] == 0 else ""))
    lines.append("You can continue on the phone line or in the website chat — we will pick up from here. (Prototype: fictional demo data.)")
    body = "\n".join(lines)
    n = notify_customer(ph, "Kohler India — summary of your conversation", body, "", channel)
    return {"ok": True, "phone": ph, "body": body, **n}


# ───────────────────────── tickets: one queue for the whole internal team ─────────────────────────
TICKET_KINDS = {"claim_review": "Warranty claim", "customer_email": "Customer email", "callback": "Call-back request",
                "product_query": "Product / info query", "order_help": "Order help", "other": "Other"}
TICKET_STATUS = ("open", "in_progress", "waiting_customer", "resolved", "closed")


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _customer_name(phone: str) -> str:
    ph = _norm_phone(phone)
    if not ph:
        return ""
    r = crm.rows("SELECT name FROM customers WHERE phone LIKE ?", f"%{ph}") or crm.rows("SELECT name FROM customer_memory WHERE phone=?", ph)
    return r[0]["name"] if r else ""


def ticket_event(ticket_id: str, actor: str, kind: str, text: str) -> None:
    c = crm.conn()
    c.execute("INSERT INTO ticket_events(ticket_id, ts, actor, kind, text) VALUES (?,?,?,?,?)", (ticket_id, _now(), actor, kind, text[:4000]))
    c.execute("UPDATE tickets SET updated_on=? WHERE id=?", (_now(), ticket_id))
    c.commit(); c.close()


def create_ticket(kind: str, phone: str, subject: str, body: str, ref: str = "", order_no: str | None = None,
                  channel: str = "chat", priority: str = "normal") -> str:
    """Every request that needs a person becomes a ticket visible to the whole team; someone takes it, works it, and
    the customer is kept informed. The full history lives in ticket_events."""
    ph = _norm_phone(phone)
    tid = "TKT-" + uuid.uuid4().hex[:6].upper()
    c = crm.conn()
    c.execute("INSERT INTO tickets(id, kind, customer_phone, customer_name, subject, body, status, priority, assigned_to, ref, order_no, channel, created_on, updated_on, resolved_on) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (tid, kind, ph, _customer_name(ph), subject[:200], body[:4000], "open", priority, None, ref, order_no, channel, _now(), _now(), None))
    c.commit(); c.close()
    ticket_event(tid, f"customer:{ph or 'unknown'}", "created", f"[{TICKET_KINDS.get(kind, kind)} via {channel}] {body}")
    crm.audit(channel, ph or "customer", "create_ticket", {"kind": kind, "subject": subject}, {"ticket_id": tid}, "queued for the internal team", "")
    return tid


def ticket_for_ref(ref: str) -> dict | None:
    r = crm.rows("SELECT * FROM tickets WHERE ref=? ORDER BY created_on DESC LIMIT 1", ref)
    return r[0] if r else None


def list_tickets(status: str | None = None, assigned_to: str | None = None, kind: str | None = None, phone: str | None = None) -> list[dict]:
    q, args = "SELECT t.*, e.name AS assignee_name FROM tickets t LEFT JOIN employees e ON e.id=t.assigned_to WHERE 1=1", []
    if status and status != "all":
        if status == "active":
            q += " AND t.status IN ('open','in_progress','waiting_customer')"
        else:
            q += " AND t.status=?"; args.append(status)
    if assigned_to:
        q += " AND t.assigned_to=?"; args.append(assigned_to)
    if kind:
        q += " AND t.kind=?"; args.append(kind)
    if phone:
        q += " AND t.customer_phone=?"; args.append(_norm_phone(phone))
    q += " ORDER BY CASE t.status WHEN 'open' THEN 0 WHEN 'in_progress' THEN 1 WHEN 'waiting_customer' THEN 2 ELSE 3 END, t.updated_on DESC LIMIT 200"
    return crm.rows(q, *args)


def get_ticket(tid: str) -> dict | None:
    t = crm.rows("SELECT t.*, e.name AS assignee_name FROM tickets t LEFT JOIN employees e ON e.id=t.assigned_to WHERE t.id=?", tid)
    if not t:
        return None
    t = t[0]
    t["events"] = crm.rows("SELECT * FROM ticket_events WHERE ticket_id=? ORDER BY id", tid)
    if t["ref"] and t["ref"].startswith("CLM-"):
        cl = crm.rows("SELECT * FROM claims WHERE id=?", t["ref"])
        t["claim"] = cl[0] if cl else None
    t["customer"] = customer_context(t["customer_phone"]) if t["customer_phone"] else None
    return t


def case_dossier(t: dict, max_transcript_turns: int = 40) -> dict:
    """Everything known about a ticket's case, as structured parts plus one text block the assistants can read:
    the request, the claim intake and coverage, photos, the customer's memory (orders, other claims/tickets, last
    interaction), the customer's call transcripts, and every note / reply / customer message on the ticket."""
    ph = _norm_phone(t.get("customer_phone"))
    parts: list[tuple[str, str]] = []
    parts.append(("Ticket", f"{t['id']} · {TICKET_KINDS.get(t['kind'], t['kind'])} · status {t['status']} · via {t['channel']} · opened {t['created_on']}"
                  + (f" · assigned to {t.get('assignee_name')}" if t.get("assignee_name") else " · unassigned")))
    parts.append(("Customer", f"{t.get('customer_name') or 'unknown'} · {ph or '—'}"))
    parts.append(("Request", (t.get("body") or "").strip()))
    cl = t.get("claim")
    coverage = None
    if cl:
        coverage = check_warranty(cl["order_no"], cl["sku"], "", "internal", "dossier") if cl.get("order_no") else {}
        intake = json.loads(cl.get("details") or "{}")
        photos = json.loads(cl.get("photos") or "[]")
        parts.append(("Claim", f"{cl['id']} on {coverage.get('product', cl['sku'])} ({cl['sku']}), order {cl['order_no']}, purchased {coverage.get('purchased', '?')}; "
                      f"status {cl['status']}; estimated cost ₹{cl['estimated_cost_inr']:,}; "
                      f"{'within' if coverage.get('covered') else 'outside'} the {coverage.get('warranty_years', '?')}-year residential warranty (expires {coverage.get('expires', '?')}); "
                      f"registered: {coverage.get('registered')}"))
        parts.append(("Reported issue", "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in intake.items() if v)))
        parts.append(("System recommendation", cl.get("recommendation") or ""))
        upload = (settings.public_base_url.rstrip("/") if settings.public_base_url else "http://localhost:8010") + f"/claim-upload/{cl.get('upload_token')}"
        parts.append(("Photos", f"{len(photos)} uploaded" + ("" if photos else f" — upload link {upload}")))
        if cl.get("decided_by"):
            parts.append(("Decision", f"{cl['status']} by {cl['decided_by']} on {cl.get('decided_on')}" + (f": {cl['decision_note']}" if cl.get("decision_note") else "")))
    ctx = t.get("customer") or (customer_context(ph) if ph else None)
    if ctx and ctx.get("known"):
        if ctx.get("last_summary"):
            parts.append(("Last interaction (memory)", ctx["last_summary"]))
        if ctx.get("orders"):
            parts.append(("Orders", "; ".join(f"{o['order_no']} ({o['order_date']}, {o['status']})" for o in ctx["orders"])))
        others = [c for c in ctx.get("claims", []) if not cl or c["claim_id"] != cl["id"]]
        if others:
            parts.append(("Other claims", "; ".join(f"{c['claim_id']} {c['sku']} {c['status']}" for c in others)))
        oth_t = [x for x in ctx.get("tickets", []) if x["id"] != t["id"]]
        if oth_t:
            parts.append(("Other tickets", "; ".join(f"{x['id']} ({TICKET_KINDS.get(x['kind'], x['kind'])}: {x['subject'][:50]}, {x['status']})" for x in oth_t)))
    calls = crm.rows("SELECT call_id, started, transcript, summary FROM transcripts WHERE phone LIKE ? AND transcript NOT LIKE '{%' ORDER BY id DESC LIMIT 2", f"%{ph}") if ph else []
    for c in calls:
        lines = [ln for ln in (c["transcript"] or "").splitlines() if ln.strip()]
        if len(lines) > max_transcript_turns:
            lines = lines[:max_transcript_turns] + [f"… ({len(lines) - max_transcript_turns} more turns)"]
        parts.append((f"Call {c['call_id']} ({c['started'][:16] if c['started'] else 'time unknown'})", (c["summary"] + "\n" if c["summary"] else "") + "\n".join(lines)))
    evs = [e for e in t.get("events", []) if e["kind"] in ("note", "reply", "customer_message", "decision", "photos", "status", "assigned")]
    if evs:
        parts.append(("Ticket history", "\n".join(f"[{e['ts'][:16]}] {e['actor']} · {e['kind']}: {e['text'][:400]}" for e in evs)))
    background_titles = {"Last interaction (memory)", "Orders", "Other claims", "Other tickets"}
    is_bg = lambda k: k in background_titles or k.startswith("Call ")  # noqa: E731
    current = [(k, v) for k, v in parts if v and not is_bg(k)]
    background = [(k, v) for k, v in parts if v and is_bg(k)]
    text = ("# CURRENT CASE — this ticket's issue; the message must be about THIS\n\n" + "\n\n".join(f"## {k}\n{v}" for k, v in current)
            + ("\n\n# BACKGROUND — reference only (other orders, earlier claims/tickets, previous calls); do not bring these up unless the current issue depends on them\n\n"
               + "\n\n".join(f"## {k}\n{v}" for k, v in background) if background else ""))
    return {"parts": [{"title": k, "text": v, "scope": "background" if is_bg(k) else "current"} for k, v in parts if v],
            "text": text, "calls": len(calls), "coverage": coverage}


def ticket_stats() -> dict:
    rows = crm.rows("SELECT status, kind, assigned_to, COUNT(*) AS n FROM tickets GROUP BY status, kind, assigned_to")
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_assignee: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + r["n"]
        if r["status"] in ("open", "in_progress", "waiting_customer"):
            by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + r["n"]
            by_assignee[r["assigned_to"] or "unassigned"] = by_assignee.get(r["assigned_to"] or "unassigned", 0) + r["n"]
    return {"by_status": by_status, "active_by_kind": by_kind, "active_by_assignee": by_assignee, "total": sum(by_status.values())}


def assign_ticket(tid: str, employee_id: str, actor: str) -> dict:
    t = crm.rows("SELECT * FROM tickets WHERE id=?", tid)
    if not t:
        return {"ok": False, "message": "ticket not found"}
    emp = crm.rows("SELECT name FROM employees WHERE id=?", employee_id)
    c = crm.conn()
    c.execute("UPDATE tickets SET assigned_to=?, status=CASE WHEN status='open' THEN 'in_progress' ELSE status END, updated_on=? WHERE id=?", (employee_id, _now(), tid))
    c.commit(); c.close()
    ticket_event(tid, actor, "assigned", f"Taken by {emp[0]['name'] if emp else employee_id}")
    return {"ok": True, "ticket_id": tid, "assigned_to": employee_id}


def set_ticket_status(tid: str, status: str, actor: str, note: str = "") -> dict:
    if status not in TICKET_STATUS:
        return {"ok": False, "message": f"status must be one of {TICKET_STATUS}"}
    c = crm.conn()
    c.execute("UPDATE tickets SET status=?, updated_on=?, resolved_on=CASE WHEN ? IN ('resolved','closed') THEN ? ELSE resolved_on END WHERE id=?",
              (status, _now(), status, _now(), tid))
    c.commit(); c.close()
    ticket_event(tid, actor, "status", f"Status → {status}" + (f": {note}" if note else ""))
    return {"ok": True, "ticket_id": tid, "status": status}


def add_ticket_note(tid: str, actor: str, text: str) -> dict:
    ticket_event(tid, actor, "note", text)
    return {"ok": True, "ticket_id": tid}


def reply_to_customer(tid: str, actor: str, text: str, set_waiting: bool = True) -> dict:
    """Message from an employee to the customer: goes out as SMS + email (simulated), is recorded on the ticket and in the
    customer's memory, so the chat and the voice agent can quote it back."""
    t = crm.rows("SELECT * FROM tickets WHERE id=?", tid)
    if not t:
        return {"ok": False, "message": "ticket not found"}
    t = t[0]
    n = notify_customer(t["customer_phone"], f"Kohler India — update on {t['ref'] or t['id']}", f"{text}\n\n(Reply on the website chat or call our care line — quote {t['id']}.)", t["ref"] or t["id"], "internal")
    ticket_event(tid, actor, "reply", text)
    remember(t["customer_phone"], "internal", f"Team replied on {t['ref'] or t['id']}: {text[:120]}")
    if set_waiting:
        set_ticket_status(tid, "waiting_customer", actor)
    return {"ok": True, "ticket_id": tid, **n}


def customer_message_on_ticket(tid: str, phone: str, text: str, channel: str) -> dict:
    """Customer follow-up on an existing ticket (chat or phone): reopens it for the team."""
    t = crm.rows("SELECT * FROM tickets WHERE id=?", tid)
    if not t:
        return {"ok": False, "message": "ticket not found"}
    ticket_event(tid, f"customer:{_norm_phone(phone)}", "customer_message", f"[{channel}] {text}")
    c = crm.conn()
    c.execute("UPDATE tickets SET status=CASE WHEN status IN ('waiting_customer','resolved','closed') THEN 'open' ELSE status END, updated_on=? WHERE id=?", (_now(), tid))
    c.commit(); c.close()
    return {"ok": True, "ticket_id": tid}


def ask_team(phone: str, subject: str, body: str, kind: str = "product_query", order_no: str | None = None, channel: str = "chat") -> dict:
    """A customer's question or request for the internal team (product information, buying help, anything else).
    Needs the customer's phone number so the team can reply and the conversation can resume on any channel."""
    ph = _norm_phone(phone)
    if not ph:
        return {"ok": False, "message": "A mobile number is needed so the team can get back to you."}
    tid = create_ticket(kind, ph, subject, body, "", order_no, channel)
    notify_customer(ph, f"We received your request ({tid})", f"Kohler India: your request \"{subject}\" is with our team as ticket {tid}. We will reply within 2 working days by SMS/email; you can also ask for an update in the website chat or on the care line.", tid, channel)
    remember(ph, channel, f"Asked the team: {subject[:80]} ({tid})")
    crm.audit(channel, ph, "ask_team", {"subject": subject, "kind": kind}, {"ticket_id": tid}, "always allowed with a phone number", "")
    return {"ok": True, "ticket_id": tid, "message": f"Your request is with Kohler Customer Care as ticket {tid}. A team member will pick it up and reply within 2 working days; you will get an SMS and email."}


def _to_inbox(kind: str, to: str, subject: str, body: str, order_no: str | None, channel: str) -> int:
    c = crm.conn()
    cur = c.execute("INSERT INTO outbox(kind, to_addr, subject, body, order_no, created_on, status, channel) VALUES (?,?,?,?,?,?,?,?)",
                    (kind, to, subject, body, order_no, datetime.utcnow().isoformat(timespec="seconds"), "unread", channel))
    c.commit(); mid = cur.lastrowid; c.close()
    return mid


def send_email_to_team(subject: str, body: str, order_no: str | None, from_addr: str, channel: str = "chat", phone: str = "") -> dict:
    if not _norm_phone(phone):
        return {"ok": False, "message": "A mobile number is needed so the team can get back to you."}
    tid = create_ticket("customer_email", phone, subject, f"From: {from_addr}\n\n{body}", "", order_no, channel)
    notify_customer(phone, f"We received your message ({tid})", f"Kohler India: your message \"{subject}\" is with our Customer Care team as ticket {tid}. We will reply within 2 working days.", tid, channel)
    remember(phone, channel, f"Emailed the team: {subject[:80]} ({tid})")
    crm.audit(channel, from_addr, "send_email_to_team", {"subject": subject, "order_no": order_no}, {"ticket_id": tid}, "always allowed with a phone number", "")
    return {"ok": True, "ticket_id": tid, "message": f"Your message is with Kohler India Customer Care as ticket {tid}. You will hear back within 2 working days by SMS/email."}


TOOLS = {
    "lookup_order": lookup_order, "register_warranty": register_warranty, "check_warranty": check_warranty,
    "open_claim": open_claim, "place_order": place_order, "request_callback": request_callback,
}
