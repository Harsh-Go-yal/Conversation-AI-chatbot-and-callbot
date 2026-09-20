"""Synthetic Legal / Compliance documents (all fictional — see render.BANNER).

Grounding: L1 follows the real Anti-Corruption and Third-Party Management page and the Supplier Code of
Conduct (FCPA, UK Bribery Act, "anything of value", no gifts to associates). L2/L3 reuse the real spec-sheet
figures (1.28 gpf / 4.8 lpf toilets, 1.5 gpm / 5.7 l/min faucets at 60 psi, 2.5 gpm showerhead). L4 references
the real Kohler India Privacy Policy (IT Act 2000, Grievance Officer, cust_service@ mailbox).
"""

DOCS = [
    # ───────────────────────── L1 Anti-Bribery & Anti-Corruption Policy ─────────────────────────
    dict(
        id="legal_anti_bribery_policy", doc_code="LC-GL-001", format="pdf",
        title="Anti-Bribery and Anti-Corruption Policy (Associate Policy)", domain="legal", region="global",
        audience="internal", sensitivity="internal", owner="Legal — Ethics & Compliance",
        version="4.2", effective_date="2025-01-15", policy_key="legal.anti_bribery",
        tags=["legal", "anti-bribery", "anti-corruption", "gifts", "hospitality", "fcpa", "uk-bribery-act", "india-pca"],
        path="legal/global/anti_bribery_anti_corruption_policy_v4.2.pdf",
        blocks=[
            ("h", "1. Commitment"),
            ("p", "For over 150 years Kohler has conducted business with integrity, transparency and accountability. This "
                  "policy implements Our Code of Conduct and the public Anti-Corruption and Third-Party Management "
                  "statement (kohlercompany.com/ethics). It applies to every associate, officer and director worldwide and "
                  "to third parties acting on the Company's behalf."),
            ("h", "2. Laws we comply with"),
            ("t", ["Law", "Key points for associates"], [
                ["US Foreign Corrupt Practices Act (FCPA)", "Prohibits offering anything of value to foreign officials to obtain or retain business; requires accurate books and records"],
                ["UK Bribery Act 2010", "Prohibits bribery of anyone, public or private; corporate offence of failing to prevent bribery"],
                ["India Prevention of Corruption Act 1988 (as amended 2018)", "Section 9 makes a commercial organisation liable if a person associated with it bribes a public servant; \"adequate procedures\" defence — this policy is part of those procedures"],
                ["Local laws", "Wherever stricter, the local law applies"],
            ]),
            ("h", "3. Prohibited conduct"),
            ("b", ["Offering, promising, giving, requesting or accepting a bribe, kickback or <b>anything of value</b> — "
                   "including sponsorships, excess commissions, internships or jobs, rebates and gifts — to improperly influence a decision.",
                   "Facilitation (\"grease\") payments to speed up routine government action. The only exception is an imminent threat to health or safety, which must be reported to Legal within 24 hours.",
                   "Using a third party (agent, distributor, consultant) to do anything the Company may not do directly.",
                   "Inaccurate or incomplete records of any payment, gift or hospitality."]),
            ("h", "4. Gifts and hospitality that Kohler gives"),
            ("p", "Modest, infrequent hospitality with a legitimate business purpose is acceptable. Cash and cash equivalents "
                  "are never acceptable. The following limits apply per recipient and are mirrored in the country Travel and "
                  "Expense addenda; the stricter of the two applies."),
            ("t", ["Region", "Business gift without approval", "Hospitality registration threshold", "Government officials / public servants"], [
                ["India (INR)", "<b>Up to ₹5,000 per recipient per year</b>", "Any single event above ₹10,000 or gift above ₹2,000 → Gifts and Hospitality Register", "No gifts. Hospitality only with Legal pre-approval and never during a tender or inspection"],
                ["All other countries (global reference)", "Local-currency equivalent of USD 100 per recipient per year", "USD 100 equivalent → Register", "No gifts. Legal pre-approval for any hospitality"],
            ]),
            ("p", "See <b>FN-IN-002 India Travel and Expense Addendum v2.1</b> (client dinner cap ₹20,000 per event, ₹5,000 "
                  "per head, pre-approval above ₹10,000) for the operational limits; other countries apply the USD 100 reference in their own addenda."),
            ("h", "5. Gifts and hospitality that Kohler receives"),
            ("p", "Associates must not accept gifts or gratuities from suppliers or prospective suppliers. The Supplier Code "
                  "of Conduct instructs suppliers not to offer them; only generally distributed promotional items that "
                  "clearly display a corporate logo are permitted, on an infrequent basis. Meals offered by customers or "
                  "partners during legitimate business meetings may be accepted if modest and reciprocal."),
            ("h", "6. Third-party due diligence"),
            ("p", "Before engaging any agent, distributor, customs broker or consultant who interacts with government bodies, "
                  "Procurement completes the Third-Party Due Diligence questionnaire; Legal approves the contract, which must "
                  "contain anti-corruption representations and audit rights (see Supplier Code of Conduct and Supplier General "
                  "Terms and Conditions)."),
            ("h", "7. Raising concerns"),
            ("p", "Report suspected violations to your manager, Legal, or the confidential Ethics Helpline. Retaliation "
                  "against good-faith reporters is prohibited. Violations may result in dismissal and referral to authorities."),
        ],
    ),

    # ───────────────────────── L2 Global Water-Efficiency Standards Matrix ─────────────────────────
    dict(
        id="legal_water_efficiency_standards_matrix", doc_code="LC-GL-007", format="pdf",
        title="Global Water-Efficiency Standards Matrix", domain="legal", region="global",
        audience="internal", sensitivity="internal", owner="Regulatory Affairs — Kitchen & Bath",
        version="2.0", effective_date="2025-06-01", policy_key="legal.water_efficiency_standards",
        tags=["legal", "compliance", "standards", "water-efficiency", "sustainability", "watersense", "bis", "wels"],
        path="legal/global/global_water_efficiency_standards_matrix_v2.0.pdf",
        blocks=[
            ("note", "Reference matrix for product, sales and compliance teams. Thresholds are simplified for internal "
                     "guidance and are illustrative in this prototype; always confirm against the current standard text "
                     "before making a certification or marketing claim."),
            ("h", "1. Why one matrix"),
            ("p", "The same product is rated under different schemes in different markets, often at different test pressures. "
                  "A faucet rated 1.5 gpm (5.7 l/min) at 60 psi (4.1 bar) in the US will show a different flow at the 3 bar "
                  "test point used by BIS IS 17953 in India. Comparisons across markets must normalise units (gallons ↔ "
                  "litres) and test pressure before drawing conclusions."),
            ("h", "2. Scheme overview"),
            ("t", ["Market", "Scheme / standard", "Body", "Label type", "Test pressure"], [
                ["United States", "EPA WaterSense (toilets: ≤1.28 gpf / 4.8 lpf; lavatory faucets: ≤1.5 gpm; showerheads: ≤2.0 gpm)", "US EPA (voluntary, with third-party certification)", "Pass/fail label", "Faucets 60 psi (4.1 bar); showerheads 80 psi"],
                ["India", "BIS IS 17953 Part 1:2023 — plumbing taps, mixers and showers; star rating 1-star to 5-star by maximum flow", "Bureau of Indian Standards (ISI mark)", "1–5 stars", "0.3 MPa (3 bar)"],
                ["India", "IS 2556 (vitreous sanitary appliances), IS 774 (flushing cisterns), IS 8931 (bib and stop taps)", "Bureau of Indian Standards", "ISI certification mark", "Per standard"],
                ["Australia / New Zealand", "WELS — Water Efficiency Labelling and Standards (AS/NZS 6400)", "Australian Government", "0-6 stars", "Per AS/NZS 6400"],
                ["Singapore", "PUB Mandatory Water Efficiency Labelling Scheme (MWELS)", "PUB, Singapore's National Water Agency", "0–4 ticks", "Per PUB test method"],
                ["European Union / UK", "Unified Water Label (voluntary industry scheme)", "Unified Water Label Association", "Colour band by litres/min or litres/flush", "3 bar"],
                ["China", "GB 25502 (toilets) / GB 25501 (faucets) water-efficiency grades", "SAMR / CNCA", "Grade 1–3 (1 = best)", "Per GB test method"],
            ]),
            ("h", "3. Illustrative thresholds used by this prototype"),
            ("t", ["Fixture", "US WaterSense", "India IS 17953 (illustrative star bands at 3 bar)", "Singapore MWELS (illustrative)", "AU WELS (illustrative)"], [
                ["Lavatory / basin faucet", "≤ 1.5 gpm (5.7 l/min) at 60 psi", "5-star ≤ 4 l/min · 4-star ≤ 6 · 3-star ≤ 8 · 2-star ≤ 10 · 1-star ≤ 12", "3 ticks ≤ 2 l/min · 2 ticks ≤ 4 · 1 tick ≤ 6", "6-star ≤ 4.5 l/min · 5-star ≤ 6 · 4-star ≤ 7.5"],
                ["Showerhead", "≤ 2.0 gpm (7.6 l/min) at 80 psi", "5-star ≤ 6 l/min · 4-star ≤ 8 · 3-star ≤ 10", "3 ticks ≤ 5 l/min · 2 ticks ≤ 7 · 1 tick ≤ 9", "3-star ≤ 9 l/min"],
                ["Toilet (full flush)", "≤ 1.28 gpf (4.8 lpf), MaP ≥ 350 g", "IS 774 / IS 2556 — dual flush 4.5/3 l typical", "3 ticks ≤ 3.5 l · 2 ticks ≤ 4 · 1 tick ≤ 4.5 (average)", "4-star ≤ 4.5/3 l dual flush"],
            ]),
            ("h", "4. Conversion and normalisation rules"),
            ("b", ["1 US gallon = 3.785 litres; 1 gpm = 3.785 l/min; 1 gpf = 3.785 lpf.",
                   "1 psi = 0.0689 bar; 60 psi = 4.14 bar; 80 psi = 5.52 bar; 3 bar = 43.5 psi.",
                   "For an aerated faucet, flow scales approximately with the square root of pressure: Q2 ≈ Q1 × √(P2/P1). "
                   "A 5.7 l/min faucet at 4.14 bar is therefore ≈ 4.9 l/min at 3 bar (before any restrictor tolerance).",
                   "Toilet flush volume does not depend on supply pressure for gravity units; pressure-assisted units are tested per ASME A112.19.2."]),
            ("h", "5. Worked example"),
            ("p", "Kohler Simplice K-596 kitchen faucet: 1.5 gpm (5.7 l/min) at 60 psi per its specification sheet. Normalised "
                  "to the BIS test point of 3 bar the expected flow is about 4.9 l/min, which would fall in the illustrative "
                  "4-star band under IS 17953 and the 2-tick band under Singapore MWELS. Kitchen faucets are outside the "
                  "WaterSense faucet specification (which covers lavatory faucets), so no WaterSense label applies."),
        ],
    ),

    # ───────────────────────── L3 India Certification & Standards Register (xlsx) ─────────────────────────
    dict(
        id="legal_in_certification_register", doc_code="LC-IN-008", format="xlsx",
        title="India Certification and Standards Register", domain="legal", region="IN",
        audience="internal", sensitivity="internal", owner="Regulatory Affairs — Kohler India",
        version="FY26 Q2", effective_date="2025-07-01", policy_key="legal.in.certification_register",
        tags=["legal", "compliance", "bis", "isi", "certification", "india", "sustainability", "watersense"],
        path="legal/in/india_certification_standards_register_fy26q2.xlsx",
        description=["Register of Indian and US certification status for the SKUs carried in the prototype corpus.",
                     "Flow and flush figures come from the real Kohler specification sheets; ISI licence numbers, star ratings, validity dates and Indian model mappings are ILLUSTRATIVE and invented for the prototype.",
                     "IS 17953 star bands follow the illustrative thresholds in LC-GL-007."],
        sheets=[
            ("Register", ["SKU", "Product", "Category", "Rated flow / flush (spec sheet)", "Normalised (l/min at 3 bar or lpf)", "US WaterSense", "Indian standard", "ISI licence no. (illustrative)", "IS 17953 star (illustrative)", "Licence valid to (illustrative)", "Notes"], [
                ["K-3609", "Cimarron® two-piece elongated Comfort Height toilet", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556 (vitreous china)", "CM/L-9112034", "n/a (toilets not star-rated)", "2027-03-31", "Sold in India as K-3609IN"],
                ["K-3493", "Highline® pressure-assisted toilet", "Toilet", "1.6 gpf", "6.0 lpf", "No (1.6 gpf)", "IS 2556", "CM/L-9112035", "n/a", "2026-12-31", "Not WaterSense; commercial use"],
                ["K-3814", "Corbelle® Comfort Height toilet (Revolution 360)", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556", "CM/L-9112036", "n/a", "2027-03-31", ""],
                ["K-3998", "Wellworth® toilet (Class Five)", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556", "CM/L-9112037", "n/a", "2027-03-31", ""],
                ["K-5481", "Two-piece round-front Comfort Height toilet", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556", "CM/L-9112038", "n/a", "2027-03-31", ""],
                ["K-3810", "One-piece Compact Elongated Comfort Height toilet (AquaPiston)", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556", "CM/L-9112039", "n/a", "2027-03-31", ""],
                ["K-4007", "One-piece round-front toilet (AquaPiston)", "Toilet", "1.28 gpf", "4.8 lpf", "Yes", "IS 2556", "CM/L-9112040", "n/a", "2027-03-31", ""],
                ["K-596", "Simplice® pull-down kitchen faucet", "Kitchen faucet", "1.5 gpm at 60 psi", "≈ 4.9 l/min", "n/a (kitchen)", "IS 17953 Part 1:2023; IS 8931", "CM/L-9223011", "4-star", "2026-09-30", "Boost mode +30% not used for rating"],
                ["K-10433", "Pull-out kitchen faucet, two-function sprayhead", "Kitchen faucet", "1.5 gpm at 60 psi", "≈ 4.9 l/min", "n/a (kitchen)", "IS 17953 Part 1:2023; IS 8931", "CM/L-9223012", "4-star", "2026-09-30", ""],
                ["K-22169", "Forté® 2.5 gpm multifunction showerhead", "Showerhead", "2.5 gpm at 80 psi", "≈ 7.0 l/min", "No (>2.0 gpm)", "IS 17953 Part 1:2023", "CM/L-9223013", "4-star", "2026-09-30", "US non-WaterSense; India 4-star under illustrative bands"],
                ["K-72775", "Artifacts® shower arm", "Accessory", "n/a", "n/a", "n/a", "n/a — no water-efficiency standard applies", "—", "n/a", "—", "Metal component; RoHS/REACH per Restricted Materials List"],
                ["98827IN-4", "Kumin™ SC lavatory faucet (India)", "Lavatory faucet", "Operating range 0.5–5.5 bar (installation guide)", "≈ 5.5 l/min (illustrative)", "n/a (India market)", "IS 17953 Part 1:2023; IS 8931", "CM/L-9223014", "3-star", "2027-01-31", "India-market SKU; rating illustrative"],
            ], [10, 44, 14, 24, 22, 14, 30, 20, 16, 16, 40]),
            ("Standards", ["Standard", "Title", "Applies to", "Mark"], [
                ["IS 2556", "Vitreous sanitary appliances (water closets, wash basins) — specification", "Toilets, basins", "ISI"],
                ["IS 774", "Flushing cisterns for water closets and urinals", "Cisterns", "ISI"],
                ["IS 8931", "Bib taps and stop taps for water services", "Taps", "ISI"],
                ["IS 17953 Part 1:2023", "Plumbing taps, mixers and showers — general technical specification with water-efficiency star rating", "Faucets, mixers, showers", "ISI + star label"],
                ["EPA WaterSense", "US EPA voluntary water-efficiency label", "Toilets, lavatory faucets, showerheads", "WaterSense label"],
                ["ASME A112.19.2 / CSA B45.1", "Ceramic plumbing fixtures", "Toilets", "Third-party listing"],
            ], [22, 70, 30, 18]),
        ],
    ),

    # ───────────────────────── L4 DPDP Readiness Note (docx, legal-restricted-lite → internal/legal) ─────────────────────────
    dict(
        id="legal_in_dpdp_readiness_note", doc_code="LC-IN-009", format="docx",
        title="Digital Personal Data Protection Act 2023 — Readiness Note (India)", domain="legal", region="IN",
        audience="internal", sensitivity="internal", owner="Legal — Kohler India / Global Data Privacy",
        version="1.1", effective_date="2026-02-01", policy_key="legal.in.dpdp_readiness",
        tags=["legal", "privacy", "india", "dpdp", "it-act", "readiness"],
        path="legal/in/dpdp_act_readiness_note_v1.1.docx",
        blocks=[
            ("h", "1. Purpose"),
            ("p", "This note tracks Kohler India Corporation Private Limited's readiness for the Digital Personal Data "
                  "Protection Act 2023 (DPDP Act) and the DPDP Rules notified in November 2025, and lists the gaps against "
                  "the current public Kohler India Privacy Policy, which is framed on the Information Technology Act 2000 and "
                  "the Reasonable Security Practices Rules. That framework remains the operative law until the relevant DPDP "
                  "provisions commence; the policy is therefore not non-compliant today, but it will need revision."),
            ("h", "2. Timeline (as understood at the date of this note)"),
            ("t", ["Milestone", "Date", "Status"], [
                ["DPDP Act enacted", "August 2023", "Done"],
                ["DPDP Rules notified", "November 2025", "Done"],
                ["Data Protection Board constituted; Consent Manager registration opens", "≈ 12 months after Rules", "In progress"],
                ["Substantive obligations for Data Fiduciaries (notice, consent, breach reporting, rights) commence", "≈ 18 months after Rules (expected mid-2027)", "Preparing"],
            ]),
            ("h", "3. Gap list against the current Kohler India Privacy Policy"),
            ("t", ["Area", "Current policy (IT Act framing)", "DPDP requirement", "Action / owner"], [
                ["Legal basis language", "References IT Act 2000 and SPDI Rules", "Reference DPDP Act and Rules; itemised notice with purpose per data item", "Redraft policy — Legal India, Q4 FY26"],
                ["Consent", "Consent by use of the website; email-based withdrawal via cust_service mailbox", "Free, specific, informed, unambiguous consent; withdrawal as easy as giving it; Consent Manager option", "Consent capture on D2C portal and CRM — IT + Legal"],
                ["Grievance handling", "Grievance Officer named per IT Rules", "Grievance mechanism with response timelines; escalation to Data Protection Board", "Retain Grievance Officer; add SLA and Board escalation text"],
                ["Breach notification", "Not specified in the public policy", "Notify the Data Protection Board and affected Data Principals; detailed report within the timeline set by the Rules (72 hours for the detailed report)", "Update PR-GL-002 Data Breach Response Playbook — Global Privacy"],
                ["Children's data", "Not addressed", "Verifiable parental consent for under-18s; no tracking or targeted advertising to children", "Age gate on portal — IT"],
                ["Retention", "\"As long as necessary\" and longer if directed by a court", "Erase when purpose is served or consent withdrawn, subject to legal retention", "Map to PR-GL-001 Data Retention Schedule"],
                ["Data Principal rights", "Correction/removal on request by email", "Access, correction, erasure, nomination, grievance redressal", "Rights-request workflow in the Privacy Center"],
            ]),
            ("h", "4. Recommendation"),
            ("p", "Mark the current Kohler India Privacy Policy as <b>review recommended</b> in the knowledge base, with a "
                  "pointer to this note, and publish the DPDP-aligned revision at least 90 days before the substantive "
                  "obligations commence."),
        ],
    ),

    # ───────────────────────── L5 Legal Hold Memo (restricted) ─────────────────────────
    dict(
        id="legal_hold_memo_project_cascade", doc_code="LC-GL-LH-2026-03", format="pdf",
        title="Legal Hold Notice — Project Cascade", domain="legal", region="global",
        audience="internal", sensitivity="restricted", owner="Legal — Litigation",
        version="1.0", effective_date="2026-03-02", policy_key="legal.legal_hold.project_cascade",
        tags=["legal", "legal-hold", "litigation", "restricted", "privileged"],
        path="legal/global/legal_hold_memo_project_cascade_RESTRICTED.pdf",
        blocks=[
            ("note", "RESTRICTED — PRIVILEGED AND CONFIDENTIAL — ATTORNEY WORK PRODUCT. Do not forward. Fictional matter "
                     "created for the prototype."),
            ("h", "1. Matter"),
            ("p", "Project Cascade concerns a potential product-liability claim relating to alleged water-supply-line "
                  "failures in a batch of shower valves shipped to distributors in the western United States between "
                  "March and August 2025. No proceedings have been filed; the Company has received a preservation demand "
                  "from counsel for two distributors."),
            ("h", "2. Who is subject to this hold"),
            ("b", ["All associates in Valve Engineering, Quality (Sheboygan), Supply Chain — Western Region, Customer Care "
                   "escalations Tier 2 and 3, and Regulatory Affairs.",
                   "The two contract manufacturers for the affected valve bodies (notified separately by Procurement)."]),
            ("h", "3. What must be preserved"),
            ("t", ["Category", "Examples", "Period"], [
                ["Design and change records", "CAD revisions, ECOs, FMEA, test reports for valve family VX-200", "1 Jan 2024 onward"],
                ["Quality and supplier records", "Incoming inspection, CAPA, supplier audits, 8D reports", "1 Jan 2024 onward"],
                ["Customer contacts", "Warranty claims, call recordings, escalation tickets mentioning leaks or supply-line failure", "1 Mar 2025 onward"],
                ["Communications", "Email, Teams, WhatsApp/SMS on Company devices, meeting notes", "1 Jan 2024 onward"],
            ]),
            ("h", "4. Instructions"),
            ("b", ["Do not delete, alter or discard any material in scope, even under the Data Retention Schedule (PR-GL-001); this hold overrides routine deletion.",
                   "Suspend auto-delete on mailboxes and Teams channels listed in Annex A (IT has been instructed).",
                   "Do not discuss the matter outside the hold group; route all external enquiries to Legal — Litigation.",
                   "Acknowledge receipt in the Legal Hold portal within 5 working days."]),
            ("h", "5. Contacts"),
            ("p", "Legal — Litigation (matter lead), Legal Operations (portal and questions). The hold remains in effect until "
                  "released in writing by Legal."),
        ],
    ),
]
