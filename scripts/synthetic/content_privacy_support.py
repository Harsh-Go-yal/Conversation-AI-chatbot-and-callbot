"""Synthetic Privacy and Customer Support documents (all fictional — see render.BANNER).

Grounding: retention periods elaborate the real Kohler Co. Privacy Notice ("retain as required to fulfil the
purposes...") and Workforce Privacy Notice; breach playbook references the real privacy contacts
(KohlerGlobalDataPrivacy@kohler.com, 1-800-923-1138, privacy.kohler.com); support documents reuse the real India
Warranty Policy IN12-B (registration required; Customer Care 1800-103-2244 Mon–Sat 08:00–20:00,
indiacustomercare@kohler.com) and the real spec-sheet figures in the product catalog.
"""

DOCS = [
    # ───────────────────────── P1 Data Retention Schedule (xlsx) ─────────────────────────
    dict(
        id="privacy_data_retention_schedule", doc_code="PR-GL-001", format="xlsx",
        title="Data Retention Schedule", domain="privacy", region="global",
        audience="internal", sensitivity="internal", owner="Global Data Privacy",
        version="3.0", effective_date="2025-03-01", policy_key="privacy.data_retention",
        tags=["privacy", "retention", "records", "gdpr", "dpdp", "ccpa"],
        path="privacy/global/data_retention_schedule_v3.0.xlsx",
        description=["Operational retention periods that implement the 'Retention of Your Information' section of the Kohler Co. Privacy Notice and the 'How long we store your personal data' section of the Workforce Privacy Notice.",
                     "Periods run from the end of the relationship or the transaction unless stated. A legal hold (see Legal) overrides every period in this schedule.",
                     "Periods are invented for the prototype."],
        sheets=[
            ("Schedule", ["Record class", "Examples", "Data subjects", "Retention — India", "Retention — United States", "Retention — EU/UK", "Legal basis / driver", "System of record", "Disposal"], [
                ["Customer account", "Profile, preferences, login", "Customers", "Until account closure + 1 year", "Until account closure + 2 years", "Until account closure + 1 year", "Contract; IT Act / DPDP; CCPA; GDPR", "CRM / D2C portal", "Delete or anonymise"],
                ["Order and transaction", "Invoices, payment records, delivery", "Customers", "8 years (Companies Act 2013; GST)", "7 years (tax)", "6 years (tax) / 10 years (DE)", "Legal obligation", "ERP", "Archive then delete"],
                ["Warranty registration and claims", "Product registration, claim history, call recordings", "Customers", "Warranty period + 3 years", "Warranty period + 3 years", "Warranty period + 3 years", "Contract; product liability", "Warranty portal / CRM", "Delete"],
                ["Customer service recordings", "Call recordings, chat transcripts", "Customers", "90 days (quality) / claim lifetime if attached to a claim", "1 year", "90 days", "Legitimate interest; consent for recording", "Contact centre platform", "Auto-delete"],
                ["Marketing consent and preferences", "Opt-in records, campaign engagement", "Prospects, customers", "Until withdrawal + 3 years (proof of consent)", "Until withdrawal + 3 years", "Until withdrawal + 3 years", "Consent (DPDP/GDPR); CAN-SPAM", "Marketing platform", "Delete"],
                ["Website analytics and cookies", "IP, device, usage events", "Visitors", "13 months", "13 months", "13 months", "Cookie Policy; consent", "Analytics platform", "Auto-delete"],
                ["Associate personnel file", "Contract, performance, disciplinary", "Associates", "Employment + 5 years", "Employment + 7 years", "Employment + 6 years", "Employment law; Workforce Privacy Notice", "Workday", "Archive then delete"],
                ["Payroll and tax", "Salary, PF/gratuity, W-2/Form 16", "Associates", "8 years", "7 years", "6 years", "Tax and social-security law", "Payroll system", "Archive then delete"],
                ["Recruitment", "Applications, interview notes", "Candidates", "1 year from decision", "2 years from decision (EEOC)", "6 months from decision", "Legitimate interest; anti-discrimination law", "ATS", "Delete"],
                ["Supplier due diligence", "Questionnaires, sanctions screening, audit reports", "Supplier contacts", "Contract + 8 years", "Contract + 7 years", "Contract + 6 years", "Anti-bribery adequate procedures; audit rights", "Procurement system", "Archive then delete"],
                ["Privacy requests", "DSAR / rights-request logs", "Any", "3 years", "2 years (CCPA: 24 months)", "3 years", "Accountability", "Privacy Center", "Delete"],
                ["Security and access logs", "System logs, badge access", "Associates, visitors", "1 year", "1 year", "6 months", "Security; IT Act reasonable security practices", "SIEM", "Auto-delete"],
            ], [26, 34, 18, 28, 28, 28, 34, 22, 18]),
        ],
    ),

    # ───────────────────────── P2 Data Breach Response Playbook (restricted) ─────────────────────────
    dict(
        id="privacy_breach_response_playbook", doc_code="PR-GL-002", format="pdf",
        title="Personal Data Breach Response Playbook", domain="privacy", region="global",
        audience="internal", sensitivity="restricted", owner="Global Data Privacy / Information Security",
        version="2.2", effective_date="2025-11-15", policy_key="privacy.breach_playbook",
        tags=["privacy", "breach", "incident-response", "gdpr", "dpdp", "us-state-law", "restricted"],
        path="privacy/global/data_breach_response_playbook_v2.2_RESTRICTED.pdf",
        blocks=[
            ("note", "RESTRICTED — for Legal, Global Data Privacy, Information Security and the Incident Commander. "
                     "Contains regulator timelines and internal escalation contacts."),
            ("h", "1. Definitions and severity"),
            ("t", ["Severity", "Definition", "Examples"], [
                ["S1 — Critical", "Confirmed exfiltration of special-category or financial data, or > 10,000 individuals", "Payment data theft; ransomware with data exfiltration"],
                ["S2 — Major", "Confirmed unauthorised access or loss affecting 100–10,000 individuals", "Misdirected bulk email; lost unencrypted laptop with customer list"],
                ["S3 — Minor", "Contained incident, < 100 individuals, low risk", "Single misaddressed invoice; internal over-permissioning corrected same day"],
            ]),
            ("h", "2. Internal clock"),
            ("b", ["<b>T+0</b>: any associate who suspects a breach reports to the IT Service Desk or KohlerGlobalDataPrivacy@kohler.com immediately.",
                   "<b>T+4 h</b>: Information Security triages and assigns severity; Incident Commander appointed for S1/S2.",
                   "<b>T+24 h</b>: Global Data Privacy completes the regulator-notification assessment for every affected jurisdiction.",
                   "<b>T+48 h</b>: Draft regulator and individual notifications ready for Legal review (S1/S2)."]),
            ("h", "3. Regulatory notification matrix"),
            ("t", ["Jurisdiction", "Regulator", "Deadline", "Individuals"], [
                ["EU / UK (GDPR / UK GDPR)", "Lead supervisory authority (Ireland DPC for EU; ICO for UK)", "72 hours from awareness, unless unlikely to result in risk", "Without undue delay if high risk"],
                ["India (DPDP Act 2023 and Rules 2025)", "Data Protection Board of India", "Initial intimation without delay; detailed report within 72 hours (extendable on request)", "Notify each affected Data Principal without delay, in plain language"],
                ["India (IT Act / CERT-In directions 2022)", "CERT-In", "Within 6 hours of noticing a reportable cyber incident", "—"],
                ["United States — state laws", "State Attorneys General (varies)", "Typically 30–60 days from discovery; some states 'without unreasonable delay'; AG notice above thresholds (e.g. 500–1,000 residents)", "Written notice to residents per state statute"],
                ["United States — California (CCPA/CPRA)", "California AG / CPPA", "Per state breach statute; private right of action for certain data", "Per statute"],
                ["Brazil (LGPD)", "ANPD", "Within 3 working days (ANPD resolution)", "Per ANPD guidance"],
            ]),
            ("h", "4. Roles"),
            ("t", ["Role", "Responsibility"], [
                ["Incident Commander (InfoSec)", "Containment, forensics, timeline"],
                ["Global Data Privacy", "Risk assessment, regulator notifications, register entry"],
                ["Legal", "Privilege, external counsel, litigation hold if required (see Legal Hold procedure)"],
                ["Communications", "Customer and associate messaging; press holding statement"],
                ["Business owner", "Affected-individual list, remediation offers"],
            ]),
            ("h", "5. Contacts and tools"),
            ("p", "Privacy Center: privacy.kohler.com · Privacy team: KohlerGlobalDataPrivacy@kohler.com · toll-free "
                  "1-800-923-1138 · India Grievance Officer per the Kohler India Privacy Policy. Incident register and "
                  "templates are in the Privacy Center admin workspace."),
        ],
    ),

    # ───────────────────────── S1 Escalation Matrix & SLAs (restricted) ─────────────────────────
    dict(
        id="support_escalation_matrix_sla", doc_code="CS-GL-001", format="pdf",
        title="Customer Care Escalation Matrix and Service Levels — India", domain="support", region="IN",
        audience="internal", sensitivity="internal", owner="Customer Care Operations",
        version="3.4", effective_date="2025-09-01", policy_key="support.escalation_matrix",
        tags=["support", "escalation", "sla", "refund-authority", "warranty", "returns", "internal"],
        path="support/in/customer_care_escalation_matrix_v3.4_INTERNAL.pdf",
        blocks=[
            ("note", "INTERNAL — for Customer Care associates and team leads. Do not quote authority limits or internal "
                     "SLAs to customers; quote only the public warranty and return policies."),
            ("h", "1. Tiers and response targets"),
            ("t", ["Tier", "Who", "First response", "Resolution target", "Typical cases"], [
                ["Tier 1", "Customer Care Executive / Representative", "Phone: immediate · Email/chat: 4 business hours", "2 business days", "Order status, product information, warranty registration, simple troubleshooting"],
                ["Tier 2", "Senior Specialist", "8 business hours", "5 business days", "Warranty claims needing parts, returns outside standard rules, installation issues"],
                ["Tier 3", "Team Lead / Technical Support Engineer", "1 business day", "10 business days", "Repeat failures, safety concerns, dealer/project escalations"],
                ["Tier 4", "Customer Care Manager / Regional Head", "1 business day", "Case by case", "Legal threats, media, regulator complaints, recalls (see CS-GL-003)"],
            ]),
            ("h", "2. Refund, replacement and goodwill authority"),
            ("t", ["Level", "Authority (INR)", "Notes"], [
                ["Tier 1", "Replacement parts up to ₹5,000; refunds only within the published Kohler India Refund Policy", "Must be logged with reason code"],
                ["Tier 2", "Refund or replacement up to ₹25,000", ""],
                ["Tier 3", "Up to ₹1,00,000", "Second approver for cash refunds above ₹50,000"],
                ["Tier 4", "Above ₹1,00,000", "Finance Business Partner co-approval"],
            ]),
            ("h", "3. Applying the public policies (agents must stay within these)"),
            ("t", ["Scenario", "India rule to quote"], [
                ["Customer requests a refund or cancellation on a kohler.co.in order", "Kohler India Terms and Conditions and Refund Policy: orders may be cancelled before dispatch for a full refund to the original payment method; refusal of delivery may attract cancellation charges; damaged-on-delivery must be reported within 48 hours with photos. Never promise a timeline beyond the Refund Policy"],
                ["Toilet or sanitaryware defect", "Warranty Policy 1677778-IN12-B: vitreous china 10 years residential / 5 years commercial; VC fittings 2 years / 1 year; product must be registered on the warranty portal and proof of purchase provided"],
                ["Intelligent toilet electronics", "IN12-B: mechanical, electronics and electrical 5 years residential / 1 year commercial with 5-year preventive maintenance (4 visits per year). Note: superseded IN12-A stated 3 years / 1 year — always quote IN12-B"],
                ["Faucet drip or leak", "IN12-B: faucet external body 10 years residential / 5 years commercial; PVD/BL finish 12 years residential; see also the Faucet Limited Warranty leaflet"],
                ["Shower enclosure / glass fittings", "Shower Door Enclosures warranty terms; Shower Glass Fittings five-year limited warranty"],
            ]),
            ("h", "4. Mandatory escalation triggers"),
            ("b", ["Any mention of injury, flooding damage above ₹1,00,000, or fire — Tier 3 immediately and Safety notified.",
                   "Any legal threat, regulator, consumer-forum or media reference — Tier 4 within 1 business day; Legal informed.",
                   "Three or more identical failures on the same SKU within 30 days — Quality notified (possible field action, CS-GL-003).",
                   "Privacy complaints or data requests — route to the Privacy Center (privacy.kohler.com) within 1 business day."]),
            ("h", "5. Contact channels (public)"),
            ("p", "India Customer Care: 1800-103-2244, Mon–Sat 08:00–20:00; indiacustomercare@kohler.com; WhatsApp "
                  "+91 124 483 2930. Kohler India Corporation Pvt. Ltd., 6th Floor, Office Tower, Ambience Island, NH-8, "
                  "Gurgaon, Haryana 122001."),
        ],
    ),

    # ───────────────────────── S2 Support Tone Guide & Email Templates (md) ─────────────────────────
    dict(
        id="support_tone_email_templates", doc_code="CS-GL-002", format="md",
        title="Customer Care Tone Guide and Email Templates (India)", domain="support", region="IN",
        audience="internal", sensitivity="internal", owner="Customer Care Operations",
        version="1.6", effective_date="2025-06-01", policy_key="support.email_templates",
        tags=["support", "templates", "email", "tone", "refund", "warranty"],
        path="support/in/customer_care_tone_guide_email_templates_v1.6.md",
        blocks=[
            ("h", "1. Tone principles"),
            ("b", ["<b>Gracious</b>: warm, calm and specific. Use the customer's name once; never blame the customer.",
                   "<b>Clear</b>: lead with the outcome, then the steps, then the policy reference.",
                   "<b>Accurate</b>: quote only published policies (Return Policy, warranties, Terms). Never quote internal authority limits.",
                   "<b>Brief</b>: under 180 words; one ask per email; bullet the steps.",
                   "Sign-off: first name, Kohler India Customer Care, and the public contact line 1800-103-2244."]),
            ("h", "2. Template — cancellation and refund confirmed (kohler.co.in order, before dispatch)"),
            ("p", "<b>Subject:</b> Your kohler.co.in order {order_number} is cancelled and your refund is on its way<br/>"
                  "Dear {first_name},<br/>As requested, we have cancelled order {order_number} ({product}) before dispatch. In "
                  "line with the Kohler India Terms and Conditions and Refund Policy, the full amount of ₹{amount} will be "
                  "refunded to the original payment method ({payment_method}); banks typically take 5–7 working days to "
                  "reflect it.<br/>If you paid by EMI or credit card, the final credit is governed by your card issuer's terms."
                  "<br/>If you would like help choosing an alternative product, just reply to this email.<br/>"
                  "Customer Care: 1800-103-2244 (Mon–Sat, 08:00–20:00) · indiacustomercare@kohler.com<br/>"
                  "Warm regards,<br/>{agent_first_name}<br/>Kohler India Customer Care"),
            ("h", "3. Template — warranty claim acknowledged (India)"),
            ("p", "<b>Subject:</b> Warranty claim {claim_number} received — {product}<br/>"
                  "Dear {first_name},<br/>Thank you for registering your {product} and raising claim {claim_number}. Your product "
                  "is covered under the Kohler India Warranty Policy (1677778-IN12-B) for {coverage_period} from the date of "
                  "purchase.<br/>What happens next:<br/>1. A Kohler service partner will contact you within 2 working days to "
                  "schedule a visit.<br/>2. Please keep your invoice and warranty registration available.<br/>3. Genuine parts "
                  "and labour for the covered defect are free of charge; civil or construction work is not covered.<br/>"
                  "Customer Care: 1800-103-2244 (Mon–Sat, 08:00–20:00) · indiacustomercare@kohler.com<br/>"
                  "Warm regards,<br/>{agent_first_name}<br/>Kohler India Customer Care"),
            ("h", "4. Template — request outside policy (declined with alternative)"),
            ("p", "<b>Subject:</b> About your request for order {order_number}<br/>"
                  "Dear {first_name},<br/>Thank you for contacting us. I have reviewed your request regarding {product}. Because "
                  "{reason_outside_policy}, I am unable to approve a refund under the Kohler India Refund Policy.<br/>What I can "
                  "offer:<br/>• If the product has a manufacturing defect, it may be covered under the Kohler India Warranty "
                  "Policy (1677778-IN12-B); I can open a warranty claim for you today — please keep your invoice and warranty "
                  "registration handy.<br/>• {alternative}<br/>Let me know which option you prefer.<br/>Customer Care: "
                  "1800-103-2244 (Mon–Sat, 08:00–20:00)<br/>Warm regards,<br/>{agent_first_name}<br/>Kohler India Customer Care"),
            ("h", "5. Template — installation or troubleshooting follow-up"),
            ("p", "<b>Subject:</b> Follow-up on your {product}<br/>Hi {first_name},<br/>Thanks for your patience. Based on "
                  "what you described, the likely cause is {cause}. Please try:<br/>1. {step_1}<br/>2. {step_2}<br/>3. "
                  "{step_3}<br/>The specification and installation guide is attached. If the issue continues, reply with a "
                  "short video and we will arrange a service visit through a Kohler service partner.<br/>Warm regards,<br/>{agent_first_name}<br/>Kohler India Customer Care"),
            ("h", "6. Do-not-say list"),
            ("b", ["\"Our policy doesn't allow it\" — say what the policy <i>does</i> allow.",
                   "Internal tier names, authority limits, SLAs, or \"my manager won't approve\".",
                   "Anything about pending legal matters, recalls not yet announced, or other customers."]),
        ],
    ),

    # ───────────────────────── S3 Product Recall / Field Action Procedure (restricted docx) ─────────────────────────
    dict(
        id="support_recall_field_action_procedure", doc_code="CS-GL-003", format="docx",
        title="Product Recall and Field Action Procedure", domain="support", region="global",
        audience="internal", sensitivity="restricted", owner="Quality — Product Compliance / Customer Care",
        version="2.0", effective_date="2025-02-01", policy_key="support.recall_procedure",
        tags=["support", "recall", "field-action", "quality", "safety", "restricted"],
        path="support/global/product_recall_field_action_procedure_v2.0_RESTRICTED.docx",
        blocks=[
            ("note", "RESTRICTED — Customer Care, Quality, Legal and Communications. Do not discuss potential field "
                     "actions with customers, dealers or media before the public notice is issued."),
            ("h", "1. Triggers"),
            ("b", ["Three or more identical failures on one SKU within 30 days reported through Customer Care (see CS-GL-001).",
                   "Any injury, fire or flooding attributed to a Kohler product.",
                   "Supplier notification of a non-conforming component (Supplier Quality Manual, corrective-action process).",
                   "Regulator enquiry (US CPSC, BIS, or equivalent)."]),
            ("h", "2. Decision process"),
            ("t", ["Step", "Owner", "Timing"], [
                ["Open a Field Action Review (FAR) case; freeze affected inventory", "Quality — Product Compliance", "Within 1 business day of trigger"],
                ["Risk assessment (severity × probability × exposure) and root-cause hypothesis", "Quality + Engineering", "5 business days"],
                ["Decision: no action / silent fix in production / service campaign / voluntary recall", "Field Action Committee (Quality, Legal, Customer Care, BU President)", "10 business days"],
                ["Regulator notification where required (e.g. CPSC within 24 hours of determining a reportable hazard)", "Legal", "Per regulation"],
                ["Public notice, dealer bulletin, Customer Care script and FAQ", "Communications + Customer Care", "Before any customer contact"],
            ]),
            ("h", "3. Customer Care actions during a field action"),
            ("b", ["Use only the approved script and FAQ; log every contact against the FAR case number.",
                   "Offer the remedy defined in the notice (repair kit, replacement, or refund) — no goodwill beyond it without Tier 4 approval.",
                   "Preserve records: field actions are frequently subject to legal hold (see Legal)."]),
            ("h", "4. Closure"),
            ("p", "A field action closes when the remedy completion rate reaches the target set by the Committee (typically "
                  "≥ 80% of affected units or 12 months), the corrective action is verified in production, and Legal confirms "
                  "regulator requirements are met."),
        ],
    ),

    # ───────────────────────── S4 Product Catalog (public xlsx, derived from real spec sheets) ─────────────────────────
    dict(
        id="support_product_catalog", doc_code="CS-GL-CAT-2026", format="xlsx",
        title="Product Catalog — Water-Efficiency Reference", domain="support", region="global",
        audience="public", sensitivity="public", owner="Product Marketing",
        version="2026.1", effective_date="2026-01-01", policy_key="support.product_catalog",
        tags=["support", "product", "catalog", "sustainability", "watersense", "water-savings", "public"],
        path="support/global/product_catalog_water_efficiency_2026.xlsx",
        description=["Structured view of the products whose real Kohler specification sheets are in the corpus. Flush and flow figures, WaterSense status, flushing technology and ADA notes are taken from those sheets.",
                     "List prices, India availability and the water-savings baseline assumptions are INVENTED for the prototype.",
                     "Savings baseline: pre-1994 US toilets used 3.5 gpf (13.2 lpf); the 1992 US Energy Policy Act limit is 1.6 gpf (6.0 lpf). Annual savings assume 5 flushes per person per day."],
        sheets=[
            ("Catalog", ["SKU", "Product", "Category", "Flush / flow (spec sheet)", "Litres", "WaterSense", "Technology", "ADA / Comfort Height", "Warranty (India, IN12-B)", "Availability", "List price USD (fictional)", "List price INR (fictional)", "Spec sheet"], [
                ["K-3609", "Cimarron® two-piece elongated toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "AquaPiston® canister, single-flush gravity", "Comfort Height®, ADA", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "IN, global", 429, 32900, "K-3609_spec.pdf"],
                ["K-3493", "Highline® pressure-assisted toilet", "Toilet", "1.6 gpf", 6.0, "No", "Sloan FLUSHMATE® pressure-assisted", "Comfort Height®, ADA", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "global", 519, 41900, "K-3493_spec.pdf"],
                ["K-3814", "Corbelle® Comfort Height toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "Revolution 360® swirl flush", "Comfort Height®, ADA", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "IN, global", 489, 37500, "K-3814_spec.pdf"],
                ["K-3998", "Wellworth® toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "Class Five® flushing", "Standard height", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "global", 279, 21900, "K-3998_spec.pdf"],
                ["K-5481", "Two-piece round-front Comfort Height toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "Class Five® flushing, single-flush gravity", "Comfort Height®, ADA", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "global", 349, 27500, "K-5481_spec.pdf"],
                ["K-3810", "One-piece Compact Elongated Comfort Height toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "AquaPiston®", "Comfort Height®, ADA", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "IN, global", 649, 49900, "K-3810_spec.pdf"],
                ["K-4007", "One-piece round-front toilet", "Toilet", "1.28 gpf", 4.8, "Yes", "AquaPiston®", "Regular height", "Vitreous china 10-yr residential / 5-yr commercial; VC fittings 2-yr", "global", 599, 45900, "K-4007_spec.pdf"],
                ["K-596", "Simplice® pull-down kitchen faucet", "Kitchen faucet", "1.5 gpm at 60 psi", 5.7, "n/a (kitchen)", "Boost Technology (+30% on demand); ceramic disc valves", "ADA", "Faucet external body 10-yr residential / 5-yr commercial", "IN, global", 379, 28900, "K-596_spec.pdf"],
                ["K-10433", "Pull-out kitchen faucet, two-function sprayhead", "Kitchen faucet", "1.5 gpm at 60 psi", 5.7, "n/a (kitchen)", "Ceramic disc valves; lower/higher flow kits available", "ADA", "Faucet external body 10-yr residential / 5-yr commercial", "global", 329, 24900, "K-10433_spec.pdf"],
                ["K-22169", "Forté® multifunction showerhead", "Showerhead", "2.5 gpm", 9.5, "No", "Multifunction spray", "—", "Faucet external body 10-yr residential / 5-yr commercial", "IN, global", 99, 7900, "K-22169_spec.pdf"],
                ["K-72775", "Artifacts® shower arm", "Accessory", "n/a", None, "n/a", "Metal construction, 1/2-in NPT", "—", "Faucet fittings 2-yr residential / 1-yr commercial", "global", 89, 6900, "K-72775_spec.pdf"],
                ["98827IN-4", "Kumin™ SC lavatory faucet (India)", "Lavatory faucet", "Operating pressure 0.5–5.5 bar, max 65 °C (install guide)", None, "n/a", "Single control; aerator", "—", "Faucet external body 10-yr residential / 5-yr commercial", "IN", None, 9900, "kumin_faucet_installation_instructions.pdf"],
            ], [10, 40, 14, 26, 8, 12, 36, 20, 36, 14, 14, 14, 30]),
            ("Savings_Model", ["Parameter", "Value", "Unit", "Source / note"], [
                ["Pre-1994 toilet baseline", 3.5, "gpf", "Common pre-EPAct toilets (illustrative baseline)"],
                ["1992 Energy Policy Act limit", 1.6, "gpf", "US federal maximum since 1994"],
                ["WaterSense maximum", 1.28, "gpf", "EPA WaterSense specification (20% below 1.6)"],
                ["Flushes per person per day", 5, "flushes", "Assumption"],
                ["Household size", 2.5, "persons", "Assumption"],
                ["Litres per gallon", 3.785, "l/gal", "Conversion"],
                ["Annual savings, 1.6 → 1.28 gpf, per household", "= (1.6-1.28) × 5 × 2.5 × 365", "gallons/yr", "≈ 1,460 gal ≈ 5,530 l"],
                ["Annual savings, 3.5 → 1.28 gpf, per household", "= (3.5-1.28) × 5 × 2.5 × 365", "gallons/yr", "≈ 10,130 gal ≈ 38,340 l"],
                ["Context", "98.1 billion", "gallons", "Water saved by Kohler WaterSense-labeled products in the US in 2024 (2024 Global Impact Report, real)"],
            ], [44, 30, 12, 70]),
        ],
    ),
]
