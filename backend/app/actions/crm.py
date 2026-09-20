"""Actions layer — a small SQLite CRM the agent is allowed to change through guarded tools.

Tables: customers, products, orders, order_items, registrations, claims, callbacks, outbox (emails), audit_log.
Every mutating tool writes an audit row (channel, actor, tool, rule applied, evidence). All data is FICTIONAL.
Warranty periods follow the real Kohler India Warranty Policy 1677778-IN12-B (residential): vitreous china 10 y,
intelligent-toilet electronics 5 y, faucet body 10 y, faucet fittings 2 y, shower glass fittings 5 y, accessories 2 y.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import ROOT

DB = ROOT / "data" / "crm.db"

WARRANTY_YEARS = {  # residential, per IN12-B (illustrative mapping by product category)
    "toilet": 10, "intelligent_toilet": 5, "faucet": 10, "faucet_fitting": 2, "showerhead": 2, "shower_enclosure": 5,
    "kitchen_sink": 5, "accessory": 2,
}
TIER1_PART_LIMIT_INR = 5000  # escalation matrix: Tier 1 may approve replacement parts up to ₹5,000 — used only as a RECOMMENDATION; every claim is decided by a person
UPLOADS = DB.parent / "uploads"      # claim photos: data/uploads/<claim_id>/


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY, name TEXT, phone TEXT, email TEXT, city TEXT);
CREATE TABLE IF NOT EXISTS products(sku TEXT PRIMARY KEY, name TEXT, category TEXT, litres REAL, price_inr INTEGER, watersense INTEGER);
CREATE TABLE IF NOT EXISTS orders(order_no TEXT PRIMARY KEY, customer_id TEXT, order_date TEXT, status TEXT, channel TEXT, total_inr INTEGER, address TEXT);
CREATE TABLE IF NOT EXISTS order_items(order_no TEXT, sku TEXT, qty INTEGER, PRIMARY KEY(order_no, sku));
CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT, sku TEXT, registered_on TEXT, channel TEXT);
CREATE TABLE IF NOT EXISTS claims(id TEXT PRIMARY KEY, order_no TEXT, sku TEXT, issue TEXT, status TEXT, decision_rule TEXT, remedy TEXT, estimated_cost_inr INTEGER, created_on TEXT, channel TEXT, details TEXT, photos TEXT, recommendation TEXT, upload_token TEXT, contact_phone TEXT, decided_by TEXT, decided_on TEXT, decision_note TEXT);
CREATE TABLE IF NOT EXISTS callbacks(id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, reason TEXT, status TEXT, created_on TEXT, channel TEXT);
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, to_addr TEXT, subject TEXT, body TEXT, order_no TEXT, created_on TEXT, status TEXT, channel TEXT);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, channel TEXT, actor TEXT, tool TEXT, args TEXT, result TEXT, rule TEXT, evidence TEXT);
CREATE TABLE IF NOT EXISTS customer_memory(phone TEXT PRIMARY KEY, name TEXT, email TEXT, last_channel TEXT, last_summary TEXT, open_items TEXT, updated_on TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, kind TEXT, subject TEXT, created_on TEXT);
CREATE TABLE IF NOT EXISTS employees(id TEXT PRIMARY KEY, name TEXT, email TEXT, role TEXT, team TEXT, tier TEXT);
CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, kind TEXT, customer_phone TEXT, customer_name TEXT, subject TEXT, body TEXT,
    status TEXT, priority TEXT, assigned_to TEXT, ref TEXT, order_no TEXT, channel TEXT, created_on TEXT, updated_on TEXT, resolved_on TEXT);
CREATE TABLE IF NOT EXISTS ticket_events(id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT, ts TEXT, actor TEXT, kind TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS transcripts(id INTEGER PRIMARY KEY AUTOINCREMENT, call_id TEXT, phone TEXT, started TEXT, transcript TEXT, summary TEXT, actions TEXT);
"""

PRODUCTS = [
    ("K-3609", "Cimarron two-piece elongated Comfort Height toilet", "toilet", 4.8, 32900, 1),
    ("K-3493", "Highline pressure-assisted toilet", "toilet", 6.0, 41900, 0),
    ("K-3814", "Corbelle Comfort Height toilet", "toilet", 4.8, 37500, 1),
    ("K-3998", "Wellworth toilet", "toilet", 4.8, 21900, 1),
    ("K-5481", "Two-piece round-front Comfort Height toilet", "toilet", 4.8, 27500, 1),
    ("K-3810", "One-piece Compact Elongated toilet", "toilet", 4.8, 49900, 1),
    ("K-4007", "One-piece round-front toilet", "toilet", 4.8, 45900, 1),
    ("K-77795IN", "Veil intelligent toilet (India)", "intelligent_toilet", 3.5, 349000, 0),
    ("K-596", "Simplice pull-down kitchen faucet", "faucet", 5.7, 28900, 0),
    ("K-10433", "Pull-out kitchen faucet, two-function sprayhead", "faucet", 5.7, 24900, 0),
    ("98827IN-4", "Kumin SC lavatory faucet", "faucet", 5.5, 9900, 0),
    ("K-22169", "Forte multifunction showerhead", "showerhead", 9.5, 7900, 0),
    ("K-72775", "Artifacts shower arm", "accessory", None, 6900, 0),
]

CUSTOMERS = [
    ("C001", "Rohan Mehta", "+919810000101", "rohan.mehta@example.in", "Gurugram"),
    ("C006", "Harsh Goyal", "+917093523468", "harsh.goyal@example.in", "Hyderabad"),      # two older orders, both registered
    ("C007", "Vaidehi Bhangdia", "+919860231200", "vaidehi.b@example.in", "Nagpur"),     # one recent order, warranty not registered
    ("C002", "Priya Nair", "+919810000102", "priya.nair@example.in", "Bengaluru"),
    ("C003", "Arjun Iyer", "+919810000103", "arjun.iyer@example.in", "Pune"),
    ("C004", "Sneha Kulkarni", "+919810000104", "sneha.k@example.in", "Mumbai"),
    ("C005", "Vikram Singh", "+919810000105", "vikram.singh@example.in", "Delhi"),
]


def _d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


ORDERS = [  # order_no, customer, days_ago, status, items[(sku, qty)]
    ("KI-2022-0412", "C001", 4 * 365 + 20, "delivered", [("K-77795IN", 1)]),          # intelligent toilet, ~4 years old → electronics still in 5-yr window
    ("KI-2025-0918", "C002", 30, "delivered", [("K-3609", 2), ("98827IN-4", 2)]),
    ("KI-2025-1102", "C003", 12, "shipped", [("K-596", 1)]),
    ("KI-2025-1120", "C004", 3, "processing", [("K-3814", 1), ("K-22169", 1)]),
    ("KI-2014-0233", "C005", 11 * 365, "delivered", [("K-3998", 1)]),                  # 11 years → outside 10-yr ceramic warranty
    ("KI-2025-1003", "C001", 45, "delivered", [("K-10433", 1)]),
    ("KI-2020-0117", "C006", 5 * 365 + 300, "delivered", [("K-3609", 1), ("98827IN-4", 2)]),   # Harsh: ~5.8 yrs — toilet still in 10-yr ceramic window, faucet fittings past 2 yrs
    ("KI-2021-0342", "C006", 5 * 365 + 100, "delivered", [("K-22169", 1)]),                     # Harsh: showerhead ~5.3 yrs — outside 2-yr warranty
    ("KI-2026-0891", "C007", 15, "delivered", [("K-3493", 1), ("K-596", 1)]),                   # Vaidehi: 15 days ago, not registered yet
]

EMPLOYEES = [  # id, name, email, role, team, tier
    ("E001", "Priya Sharma", "priya.sharma@kohler.example", "Customer Care Lead", "customer_care", "Tier 2"),
    ("E002", "Arjun Nair", "arjun.nair@kohler.example", "Service Engineer", "field_service", "Tier 2"),
    ("E003", "Meera Iyer", "meera.iyer@kohler.example", "Warranty Desk Specialist", "warranty", "Tier 2"),
    ("E004", "Rahul Verma", "rahul.verma@kohler.example", "Sales Support Executive", "sales", "Tier 1"),
    ("E005", "Kavya Reddy", "kavya.reddy@kohler.example", "Customer Care Agent", "customer_care", "Tier 1"),
]
REGISTERED_AT_SEED = [("KI-2020-0117", "K-3609"), ("KI-2020-0117", "98827IN-4"), ("KI-2021-0342", "K-22169"), ("KI-2022-0412", "K-77795IN")]


def init(reset: bool = False) -> None:
    if reset and DB.exists():
        DB.unlink()
    c = conn()
    c.executescript(SCHEMA)
    # migrate an existing demo DB created before the human-in-the-loop claim intake
    have = {r[1] for r in c.execute("PRAGMA table_info(claims)").fetchall()}
    for col in ("details", "photos", "recommendation", "upload_token", "contact_phone", "decided_by", "decided_on", "decision_note"):
        if col not in have:
            c.execute(f"ALTER TABLE claims ADD COLUMN {col} TEXT")
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", PRODUCTS)
        c.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
        for order_no, cust, days_ago, status, items in ORDERS:
            total = sum(next(p[4] for p in PRODUCTS if p[0] == sku) * qty for sku, qty in items)
            city = next(x[4] for x in CUSTOMERS if x[0] == cust)
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (order_no, cust, _d(days_ago), status, "kohler.co.in", total, f"{city}, India"))
            c.executemany("INSERT INTO order_items VALUES (?,?,?)", [(order_no, sku, qty) for sku, qty in items])
        for order_no, sku in REGISTERED_AT_SEED:
            od = next(o for o in ORDERS if o[0] == order_no)
            c.execute("INSERT INTO registrations(order_no, sku, registered_on, channel) VALUES (?,?,?,?)", (order_no, sku, _d(od[2] - 7), "kohler.co.in"))
    if c.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        c.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?)", EMPLOYEES)
    # customers/orders added after the first seed (idempotent top-up for an existing demo DB)
    for cust in CUSTOMERS:
        c.execute("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?)", cust)
    for order_no, cust, days_ago, status, items in ORDERS:
        if not c.execute("SELECT 1 FROM orders WHERE order_no=?", (order_no,)).fetchone():
            total = sum(next(p[4] for p in PRODUCTS if p[0] == sku) * qty for sku, qty in items)
            city = next(x[4] for x in CUSTOMERS if x[0] == cust)
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (order_no, cust, _d(days_ago), status, "kohler.co.in", total, f"{city}, India"))
            c.executemany("INSERT INTO order_items VALUES (?,?,?)", [(order_no, sku, qty) for sku, qty in items])
            for o2, sku in REGISTERED_AT_SEED:
                if o2 == order_no:
                    c.execute("INSERT INTO registrations(order_no, sku, registered_on, channel) VALUES (?,?,?,?)", (order_no, sku, _d(days_ago - 7), "kohler.co.in"))
        # one pre-registered product
        c.execute("INSERT INTO registrations(order_no, sku, registered_on, channel) VALUES (?,?,?,?)", ("KI-2022-0412", "K-77795IN", _d(4 * 365 + 10), "web"))
    c.commit(); c.close()


def audit(channel: str, actor: str, tool: str, args: dict, result: dict, rule: str, evidence: str) -> None:
    c = conn()
    c.execute("INSERT INTO audit_log(ts, channel, actor, tool, args, result, rule, evidence) VALUES (?,?,?,?,?,?,?,?)",
              (datetime.utcnow().isoformat(timespec="seconds"), channel, actor, tool, json.dumps(args, default=str),
               json.dumps(result, default=str)[:2000], rule, evidence))
    c.commit(); c.close()


def rows(sql: str, *params) -> list[dict]:
    c = conn()
    out = [dict(r) for r in c.execute(sql, params).fetchall()]
    c.close()
    return out
