"""Synthetic Finance documents (all fictional — see render.BANNER).

Grounding: thresholds concern hospitality and gifts that Kohler GIVES to customers/partners. The real
Supplier Code of Conduct (Rev 12, Oct 2024) states that suppliers must not offer gifts or gratuities to
Kohler associates, so receiving gifts is treated as prohibited, not thresholded. Anti-bribery wording
follows the real Anti-Corruption and Third-Party Management page ("anything of value").
"""

_T_E_COMMON_INTRO = (
    "This policy sets the rules for business travel and expenses incurred by associates of Kohler Co. and its "
    "subsidiaries. It works together with <b>LC-GL-001 Anti-Bribery and Anti-Corruption Policy</b>: any meal, gift or "
    "hospitality that lacks a legitimate business purpose, or could be perceived as an attempt to improperly influence a "
    "decision, is prohibited regardless of amount (see kohlercompany.com/ethics — Anti-Corruption and Third-Party "
    "Management). Suppliers may not offer gifts or gratuities to Kohler associates (Supplier Code of Conduct, Rev 12)."
)

DOCS = [
    # ───────────────────────── F1 Global T&E ─────────────────────────
    dict(
        id="fin_global_travel_expense", doc_code="FN-GL-001", format="pdf",
        title="Global Travel and Expense Policy", domain="finance", region="global",
        audience="internal", sensitivity="internal", owner="Global Finance — Controllership",
        version="5.0", effective_date="2025-01-01", policy_key="finance.travel_expense",
        tags=["finance", "travel", "expense", "reimbursement", "hospitality"],
        path="finance/global/global_travel_expense_policy_v5.0.pdf",
        blocks=[
            ("h", "1. Purpose and principles"),
            ("p", _T_E_COMMON_INTRO),
            ("b", ["Spend Company money as carefully as your own; choose the lowest reasonable cost.",
                   "Every expense needs a business purpose, a receipt (itemised for meals and hotels) and the names of attendees.",
                   "Submit claims in Concur within 30 days of the expense; claims older than 90 days are not reimbursed.",
                   "Country addenda (for example <b>FN-IN-002 India T&E Addendum</b>) set local limits and prevail over this policy where they differ."]),
            ("h", "2. Approval and pre-approval"),
            ("t", ["Item", "Rule"], [
                ["Domestic travel", "Manager approval in Concur before booking"],
                ["International travel", "Manager + Director approval; Legal/Tax notified for trips over 30 days"],
                ["Client entertainment above the country pre-approval threshold", "Manager approval before the event; Legal approval if any attendee is a government official"],
                ["Any hospitality for a government official or state-owned enterprise employee", "Legal pre-approval always required (see LC-GL-001)"],
            ]),
            ("h", "3. Air, rail and ground"),
            ("b", ["Economy class for flights under 6 hours; premium economy over 6 hours; business class over 9 hours with Director approval.",
                   "Book through the Company travel tool at least 14 days in advance where possible.",
                   "Rental cars: intermediate class; decline additional insurance in countries where Company cover applies.",
                   "Personal car mileage is reimbursed at the rate in the country addendum (India: FN-IN-002)."]),
            ("h", "4. Lodging and meals"),
            ("p", "Hotel and meal limits are set per country in the addenda. Where a per-diem applies, no receipts are "
                  "required for meals within the per-diem; actual costs above per-diem are not reimbursed. Alcohol is "
                  "reimbursable only as part of client entertainment within the country limit."),
            ("h", "5. Client entertainment and business gifts"),
            ("p", "Client meals and business gifts are permitted only for legitimate relationship or business-development "
                  "purposes, must be reasonable and infrequent, and must be recorded in the Gifts and Hospitality Register "
                  "when above the country registration threshold. Cash or cash-equivalent gifts (vouchers, gift cards) are "
                  "never permitted. Country caps: see the addendum for your entity."),
            ("h", "6. Non-reimbursable items"),
            ("b", ["Traffic fines, personal entertainment, spouse/partner travel, minibar, laundry on trips under 5 nights, "
                   "upgrades without approval, and any item lacking a receipt where one is required."]),
            ("h", "7. Corporate cards"),
            ("p", "Associates who travel more than four times a year are issued a corporate card under <b>FN-GL-004 Corporate "
                  "Card Policy</b>. Personal use of the corporate card is prohibited."),
            ("h", "8. Audit and non-compliance"),
            ("p", "Internal Audit samples 5% of claims monthly. Policy breaches result in non-reimbursement and may lead to "
                  "disciplinary action under the Employee Handbook (HR-GL-001)."),
        ],
    ),

    # ───────────────────────── F2 India T&E Addendum v1.4 (superseded) ─────────────────────────
    dict(
        id="fin_in_te_addendum_v1_4", doc_code="FN-IN-002", format="pdf",
        title="India Travel and Expense Addendum", domain="finance", region="IN",
        audience="internal", sensitivity="internal", owner="Finance India",
        version="1.4", effective_date="2023-04-01", policy_key="finance.in.te_addendum",
        tags=["finance", "travel", "expense", "india", "hospitality", "gifts", "version-history"],
        path="finance/in/india_travel_expense_addendum_v1.4_2023.pdf",
        blocks=[
            ("note", "Version 1.4 — effective 1 April 2023 (FY24). Superseded by Version 2.1 (effective 1 April 2025). "
                     "Retained for record purposes."),
            ("h", "1. Scope"),
            ("p", "Applies to associates of Kohler India Corporation Private Limited and to visitors travelling in India. "
                  "Read with FN-GL-001 Global Travel and Expense Policy and LC-GL-001 Anti-Bribery and Anti-Corruption Policy."),
            ("h", "2. Domestic travel limits (INR)"),
            ("t", ["Item", "Metro (Delhi NCR, Mumbai, Bengaluru, Chennai, Hyderabad, Pune, Kolkata)", "Non-metro"], [
                ["Hotel per night (incl. taxes)", "₹8,000", "₹5,500"],
                ["Meal per-diem per day (own meals)", "₹2,500", "₹1,800"],
                ["Local conveyance", "Actuals (app-based cab or metro)", "Actuals"],
                ["Own car mileage", "₹12 per km", "₹12 per km"],
            ]),
            ("h", "3. Client entertainment and business gifts"),
            ("t", ["Item", "Limit / rule"], [
                ["Client meal or dinner", "<b>Maximum ₹15,000 per event</b> and ₹3,500 per head; manager approval before the event if above ₹25,000 (pre-approval threshold)"],
                ["Business gift to a customer or partner", "<b>Maximum ₹3,000 per recipient per year</b> without approval; Legal approval above that"],
                ["Registration in Gifts and Hospitality Register", "Required for any single event or gift above ₹3,000"],
                ["Government officials / PSU employees", "No gifts; hospitality only with Legal pre-approval (LC-GL-001)"],
            ]),
            ("h", "4. Air travel"),
            ("p", "Economy class on all domestic sectors. International sectors per FN-GL-001. Tickets booked through the "
                  "approved travel desk; personal frequent-flyer accrual is permitted."),
            ("h", "5. Claims"),
            ("p", "Submit in Concur within 30 days with GST-compliant invoices where available. Advances are settled within "
                  "15 days of return."),
        ],
    ),

    # ───────────────────────── F3 India T&E Addendum v2.1 (current) ─────────────────────────
    dict(
        id="fin_in_te_addendum_v2_1", doc_code="FN-IN-002", format="pdf",
        title="India Travel and Expense Addendum", domain="finance", region="IN",
        audience="internal", sensitivity="internal", owner="Finance India",
        version="2.1", effective_date="2025-04-01", policy_key="finance.in.te_addendum", supersedes="1.4",
        tags=["finance", "travel", "expense", "india", "hospitality", "gifts", "version-history"],
        path="finance/in/india_travel_expense_addendum_v2.1_2025.pdf",
        blocks=[
            ("note", "Version 2.1 — effective 1 April 2025 (FY26). Supersedes Version 1.4 (1 April 2023). Summary of "
                     "changes: client dinner cap raised from ₹15,000 to ₹20,000 per event; business-gift limit aligned to "
                     "LC-GL-001 at ₹5,000; pre-approval threshold for client entertainment lowered from ₹25,000 to ₹10,000; "
                     "hotel and per-diem limits revised."),
            ("h", "1. Scope"),
            ("p", "Applies to associates of Kohler India Corporation Private Limited and to visitors travelling in India. "
                  "Read with FN-GL-001 Global Travel and Expense Policy and LC-GL-001 Anti-Bribery and Anti-Corruption Policy."),
            ("h", "2. Domestic travel limits (INR)"),
            ("t", ["Item", "Metro (Delhi NCR, Mumbai, Bengaluru, Chennai, Hyderabad, Pune, Kolkata)", "Non-metro"], [
                ["Hotel per night (incl. taxes)", "₹10,000", "₹7,000"],
                ["Meal per-diem per day (own meals)", "₹3,000", "₹2,200"],
                ["Local conveyance", "Actuals (app-based cab or metro)", "Actuals"],
                ["Own car mileage", "₹14 per km", "₹14 per km"],
            ]),
            ("h", "3. Client entertainment and business gifts"),
            ("t", ["Item", "Limit / rule"], [
                ["Client meal or dinner", "<b>Maximum ₹20,000 per event</b> and ₹5,000 per head; <b>manager approval before the event if above ₹10,000</b> (pre-approval threshold)"],
                ["Business gift to a customer or partner", "<b>Maximum ₹5,000 per recipient per year</b> without approval; Legal approval above that (aligned with LC-GL-001)"],
                ["Registration in Gifts and Hospitality Register", "Required for any single event above ₹10,000 or any gift above ₹2,000"],
                ["Government officials / PSU employees", "No gifts; hospitality only with Legal pre-approval (LC-GL-001)"],
                ["Receiving gifts from suppliers", "Not permitted — suppliers are instructed not to offer gifts or gratuities to Kohler associates (Supplier Code of Conduct)"],
            ]),
            ("h", "4. Air travel"),
            ("p", "Economy class on all domestic sectors. International sectors per FN-GL-001. Tickets booked through the "
                  "approved travel desk; personal frequent-flyer accrual is permitted."),
            ("h", "5. Claims"),
            ("p", "Submit in Concur within 30 days with GST-compliant invoices where available. Advances are settled within "
                  "15 days of return. Claims for client entertainment must list every attendee and their organisation."),
        ],
    ),

    # ───────────────────────── F5 Corporate Card Policy (docx) ─────────────────────────
    dict(
        id="fin_corporate_card_policy", doc_code="FN-GL-004", format="docx",
        title="Corporate Card Policy", domain="finance", region="global",
        audience="internal", sensitivity="internal", owner="Global Finance — Treasury",
        version="2.0", effective_date="2024-07-01", policy_key="finance.corporate_card",
        tags=["finance", "corporate-card", "expense"],
        path="finance/global/corporate_card_policy_v2.0.docx",
        blocks=[
            ("h", "1. Eligibility and issuance"),
            ("p", "Corporate cards are issued to associates who travel four or more times a year or who regularly incur "
                  "business expenses, on manager request through the Treasury portal. The card is issued in the associate's "
                  "name; liability for approved business expenses rests with the Company."),
            ("h", "2. Permitted and prohibited use"),
            ("t", ["Permitted", "Prohibited"], [
                ["Travel, lodging, meals and client entertainment within FN-GL-001 and the country addendum", "Any personal purchase, even if repaid"],
                ["Conference fees, professional memberships approved by the manager", "Cash withdrawals (except emergencies abroad, with Treasury notice within 24 hours)"],
                ["Small business purchases under USD 500 / INR 40,000 where no purchase order is practical", "Capital equipment, software subscriptions, or anything that requires a purchase order"],
                ["", "Gifts to government officials or anything prohibited by LC-GL-001"],
            ]),
            ("h", "3. Limits"),
            ("p", "Default monthly limit USD 5,000 (INR 4,00,000). Temporary increases for extended travel are approved by "
                  "the Director and Treasury. Single-transaction limit USD 2,500 unless pre-approved."),
            ("h", "4. Reconciliation"),
            ("p", "All card transactions must be reconciled in Concur within 30 days of the statement date with receipts. "
                  "Unreconciled transactions after 60 days are deducted from payroll where local law permits, and the card "
                  "is suspended after two consecutive late statements."),
            ("h", "5. Loss, theft and departure"),
            ("p", "Report a lost or stolen card to the issuer and Treasury within 24 hours. Cards are cancelled on the last "
                  "working day; outstanding balances are settled before final pay."),
        ],
    ),

    # ───────────────────────── F6 CapEx Approval Matrix (restricted xlsx) ─────────────────────────
    dict(
        id="fin_capex_approval_matrix", doc_code="FN-GL-005", format="xlsx",
        title="Capital Expenditure Approval Matrix", domain="finance", region="global",
        audience="internal", sensitivity="restricted", owner="Global Finance — FP&A",
        version="3.1", effective_date="2025-04-01", policy_key="finance.capex_matrix",
        tags=["finance", "capex", "approval", "delegation-of-authority", "manager-only"],
        path="finance/global/capex_approval_matrix_v3.1_RESTRICTED.xlsx",
        description=["Delegation of authority for capital projects. Amounts are the total project value; approvals are cumulative (each level above the threshold must also approve).",
                     "RESTRICTED — for managers, FP&A and Internal Audit. Values are invented for the prototype."],
        sheets=[
            ("Thresholds_USD", ["Project value (USD)", "Approver 1", "Approver 2", "Approver 3", "Lead time"], [
                ["Up to 25,000", "Plant / Site Manager", "Finance Business Partner", "—", "5 working days"],
                ["25,001 – 250,000", "Director", "Finance Director", "—", "10 working days"],
                ["250,001 – 1,000,000", "Business Unit President", "Chief Financial Officer", "—", "20 working days"],
                ["1,000,001 – 10,000,000", "Chief Financial Officer", "Chief Executive Officer", "Capital Committee", "Quarterly Capital Committee"],
                ["Above 10,000,000", "Chief Executive Officer", "Board of Directors", "—", "Board calendar"],
            ], [24, 28, 28, 22, 26]),
            ("Thresholds_INR", ["Project value (INR)", "Approver 1", "Approver 2", "Approver 3", "Lead time"], [
                ["Up to ₹20 lakh", "Plant / Site Manager", "Finance Business Partner", "—", "5 working days"],
                ["₹20 lakh – ₹2 crore", "Director", "Finance Director India", "—", "10 working days"],
                ["₹2 crore – ₹8 crore", "Managing Director, Kohler India", "Chief Financial Officer", "—", "20 working days"],
                ["₹8 crore – ₹80 crore", "Chief Financial Officer", "Chief Executive Officer", "Capital Committee", "Quarterly Capital Committee"],
                ["Above ₹80 crore", "Chief Executive Officer", "Board of Directors", "—", "Board calendar"],
            ], [24, 30, 28, 22, 26]),
            ("Rules", ["Rule", "Detail"], [
                ["Splitting", "Projects may not be split to stay under a threshold; related spend within 12 months is aggregated."],
                ["Sustainability projects", "Water- and energy-saving projects with payback under 4 years may use the fast-track lane (one level lower) up to USD 1M."],
                ["Emergency", "Safety-critical repairs may proceed on Site Manager approval with retrospective approval within 10 days."],
                ["FX", "INR thresholds are set annually at the budget rate (FY26: 83 INR/USD)."],
            ], [24, 110]),
        ],
    ),

    # ───────────────────────── F7 Pre-release financial summary (restricted) ─────────────────────────
    dict(
        id="fin_q2_fy26_prerelease", doc_code="FN-GL-Q2FY26", format="pdf",
        title="Q2 FY26 Pre-release Financial Summary — Kitchen & Bath Group", domain="finance", region="global",
        audience="internal", sensitivity="restricted", owner="Global Finance — FP&A",
        version="draft 3", effective_date="2025-10-10", policy_key="finance.quarterly_prerelease",
        tags=["finance", "quarterly-results", "pre-release", "restricted", "manager-only"],
        path="finance/global/q2_fy26_prerelease_financial_summary_RESTRICTED.pdf",
        blocks=[
            ("note", "RESTRICTED — PRE-RELEASE. Not for distribution outside the senior leadership team before the "
                     "internal results call. All figures are fictional and illustrative."),
            ("h", "1. Headline results (USD millions)"),
            ("t", ["Metric", "Q2 FY26", "Q2 FY25", "Change"], [
                ["Net sales", "1,842", "1,765", "+4.4%"],
                ["Gross margin", "38.6%", "37.2%", "+140 bps"],
                ["Operating income", "231", "204", "+13.2%"],
                ["Operating margin", "12.5%", "11.6%", "+90 bps"],
                ["Free cash flow", "168", "121", "+38.8%"],
            ]),
            ("h", "2. Regional commentary"),
            ("b", ["<b>North America</b>: sales +3.1%; showroom and e-commerce channels offset softer wholesale; WaterSense-labeled toilet mix up to 71% of units.",
                   "<b>India</b>: sales +14.8% in INR terms; Jhagadia plant utilisation 86%; D2C portal revenue doubled from a small base.",
                   "<b>EMEA</b>: flat; Kohler Mira UK impacted by weak housing completions.",
                   "<b>China / APAC</b>: −2.6%; destocking at distributors expected to complete in Q3."]),
            ("h", "3. Outlook and risks"),
            ("p", "Full-year guidance maintained at +4% to +6% net sales growth. Risks: tariff changes on vitreous china "
                  "imports, brass input costs, and INR depreciation. Water-efficiency regulation (EPA WaterSense v1.2 "
                  "updates, BIS IS 17953 labelling in India) is a tailwind for the premium portfolio."),
            ("h", "4. Distribution"),
            ("p", "Senior Leadership Team, Business Unit Presidents, Finance Directors. Do not forward."),
        ],
    ),
]
