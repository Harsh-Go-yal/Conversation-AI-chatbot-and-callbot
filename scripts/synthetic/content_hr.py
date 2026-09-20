"""Synthetic HR documents (all fictional — see render.BANNER)."""

DOCS = [
    # ───────────────────────── H1 Employee Handbook ─────────────────────────
    dict(
        id="hr_employee_handbook", doc_code="HR-GL-001", format="pdf",
        title="Global Employee Handbook", domain="hr", region="global",
        audience="internal", sensitivity="internal", owner="Global Human Resources",
        version="3.2", effective_date="2025-01-01", policy_key="hr.employee_handbook",
        tags=["hr", "handbook", "conduct", "leave-overview", "it-usage"],
        path="hr/global/employee_handbook_v3.2.pdf",
        blocks=[
            ("h", "1. Purpose and scope"),
            ("p", "This Handbook summarises the employment framework that applies to all associates of Kohler Co. and its "
                  "subsidiaries worldwide (\"the Company\"). Where a country-specific policy exists (for example the India "
                  "Leave Policy), the country policy prevails on that topic. "
                  "Nothing in this Handbook creates a contract of employment."),
            ("h", "2. Our values"),
            ("b", ["<b>Gracious living</b> — we design products and workplaces that improve daily life.",
                   "<b>Believing in Better</b> — continuous improvement in quality, sustainability and safety.",
                   "<b>Integrity</b> — we comply with Our Code of Conduct (kohlercompany.com/ethics), the Global Human Rights Policy, anti-bribery rules and all applicable laws.",
                   "<b>Respect</b> — zero tolerance for harassment, discrimination or retaliation, consistent with the Global Human Rights Policy (freedom of association, no child or forced labour, fair working hours)."]),
            ("h", "3. Working hours and attendance"),
            ("p", "Standard full-time hours are 40 per week (India: 45 hours across a 5.5-day or 5-day pattern as set by the "
                  "site). Flexible start times between 07:30 and 10:00 are available for eligible roles with manager approval. "
                  "Associates must record attendance in the HR system (Workday) daily; repeated unrecorded absence is a "
                  "disciplinary matter."),
            ("h", "4. Leave — overview"),
            ("p", "Leave entitlements are set by the country leave policy. As a global minimum, all associates receive: paid "
                  "annual leave of at least 15 working days; paid sick leave; public holidays per the site calendar; and "
                  "parental leave that meets or exceeds local statutory requirements. See <b>HR-IN-002 India Leave Policy</b> "
                  "for the binding entitlements in India; other countries have their own leave schedules."),
            ("h", "5. Compensation and benefits"),
            ("p", "Pay is reviewed annually in the April cycle. Salary ranges are confidential and are shared with people "
                  "managers only (see HR-GL-006 Compensation Bands — restricted). Benefits include medical insurance for the "
                  "associate and dependants, retirement contributions per local scheme (401(k) match in the US; Provident Fund "
                  "and Gratuity in India), well-being resources, an Employee Assistance Programme and a product purchase discount of 30%. "
                  "Career development, leadership training and performance assessments are delivered through the Kohler Talent Academy."),
            ("h", "6. Code of Conduct and ethics"),
            ("p", "All associates complete annual ethics training. Gifts, meals and hospitality involving third parties must "
                  "follow <b>LC-GL-001 Anti-Bribery and Anti-Corruption Policy</b> and the applicable Travel and Expense policy. "
                  "Concerns may be raised through a manager, HR, Legal, or the confidential Ethics Helpline; retaliation "
                  "against anyone who raises a concern in good faith is prohibited."),
            ("h", "7. Information technology and data"),
            ("b", ["Company devices and accounts are for business use; incidental personal use is permitted.",
                   "Never share passwords or multi-factor tokens. Report a lost device within 4 hours to IT Service Desk.",
                   "Associate personal data is handled under the Kohler Workforce Privacy Notice; customer data under the Kohler Co. "
                   "Privacy Notice; retention periods follow the Data Retention Schedule (PR-GL-001).",
                   "Generative-AI tools may be used only through Company-approved platforms; restricted information must "
                   "never be entered into external AI services."]),
            ("h", "8. Health, safety and environment"),
            ("p", "Every associate has stop-work authority when a task is unsafe. Manufacturing sites follow the site HSE "
                  "manual; office associates complete the annual ergonomics and fire-safety modules. Environmental targets "
                  "(net-zero operations by 2035, water stewardship) are part of every site's objectives. Kohler WaterSense-labeled "
                  "products saved 98.1 billion gallons of water in the U.S. in 2024 (2024 Global Impact Report)."),
            ("h", "9. Separation"),
            ("p", "Notice periods: 30 days (individual contributors), 60 days (managers), or as stated in the employment "
                  "contract and local law. Unused earned leave is encashed per the country leave policy. Company property "
                  "and data must be returned before the last working day."),
            ("h", "10. Related documents"),
            ("t", ["Code", "Document"], [
                ["HR-IN-002", "India Leave Policy (current version 2.0)"],
                ["HR-GL-004", "Remote and Hybrid Work Policy"],
                ["HR-GL-005", "Performance Review and Promotion Guidelines (restricted)"],
                ["HR-GL-006", "Compensation Bands FY26 (restricted)"],
                ["FN-GL-001", "Global Travel and Expense Policy"],
                ["LC-GL-001", "Anti-Bribery and Anti-Corruption Policy"],
                ["—", "Our Code of Conduct (kohlercompany.com/ethics) — real"],
                ["—", "Global Human Rights Policy (kohlercompany.com/human-rights) — real"],
                ["—", "Kohler Workforce Privacy Notice (Rest of World) — real"],
            ]),
        ],
    ),

    # ───────────────────────── H2 India Leave Policy v1.0 (superseded) ─────────────────────────
    dict(
        id="hr_in_leave_policy_v1", doc_code="HR-IN-002", format="pdf",
        title="India Leave Policy", domain="hr", region="IN",
        audience="internal", sensitivity="internal", owner="HR India",
        version="1.0", effective_date="2023-01-01", policy_key="hr.in.leave_policy",
        tags=["hr", "leave", "india", "maternity", "paternity", "version-history"],
        path="hr/in/india_leave_policy_v1.0_2023.pdf",
        blocks=[
            ("note", "Version 1.0 — effective 1 January 2023. This version has been superseded by Version 2.0 "
                     "(effective 1 April 2025) and is retained for record purposes only."),
            ("h", "1. Scope"),
            ("p", "Applies to all permanent associates of Kohler India Corporation Private Limited. Statutory entitlements "
                  "under the Maternity Benefit Act 1961 (as amended 2017), the Factories Act 1948 and applicable state Shops "
                  "and Establishments Acts are minimums; where this policy is more generous, the policy applies."),
            ("h", "2. Leave entitlements"),
            ("t", ["Leave type", "Entitlement", "Conditions"], [
                ["Earned Leave (EL)", "18 working days per calendar year", "Accrues 1.5 days/month; may be taken after 3 months of service"],
                ["Casual Leave (CL)", "8 days per year", "Maximum 3 consecutive days; not carried forward"],
                ["Sick Leave (SL)", "10 days per year", "Medical certificate required beyond 2 consecutive days"],
                ["Maternity Leave", "26 weeks paid (first two children); 12 weeks thereafter", "Per Maternity Benefit Act; up to 8 weeks may be taken before the expected date"],
                ["Paternity Leave", "<b>5 working days</b> paid", "Within 30 days of the birth"],
                ["Adoption Leave", "Not provided beyond statutory (12 weeks for commissioning/adopting mothers of a child under 3 months)", "—"],
                ["Bereavement Leave", "3 days", "Immediate family"],
                ["Public Holidays", "10 per year per site calendar", "Includes 3 national holidays"],
            ]),
            ("h", "3. Carry-forward and encashment"),
            ("p", "Unused Earned Leave may be carried forward up to a maximum accumulation of <b>30 days</b>. Balances above "
                  "30 days lapse on 31 December. Earned Leave is encashed at basic salary on separation."),
            ("h", "4. Application and approval"),
            ("p", "Leave is applied in Workday at least 7 days in advance (Earned Leave) or as soon as practicable (Sick and "
                  "Casual Leave). Managers respond within 2 working days. Leave during the quarter-end close (last 5 working "
                  "days of March, June, September and December) requires second-level approval for Finance associates."),
            ("h", "5. Questions"),
            ("p", "Contact HR India at hr.india@kohler.example or the People Services portal."),
        ],
    ),

    # ───────────────────────── H3 India Leave Policy v2.0 (current) ─────────────────────────
    dict(
        id="hr_in_leave_policy_v2", doc_code="HR-IN-002", format="pdf",
        title="India Leave Policy", domain="hr", region="IN",
        audience="internal", sensitivity="internal", owner="HR India",
        version="2.0", effective_date="2025-04-01", policy_key="hr.in.leave_policy", supersedes="1.0",
        tags=["hr", "leave", "india", "maternity", "paternity", "adoption", "version-history"],
        path="hr/in/india_leave_policy_v2.0_2025.pdf",
        blocks=[
            ("note", "Version 2.0 — effective 1 April 2025. Supersedes Version 1.0 (1 January 2023). Summary of changes: "
                     "paternity leave increased from 5 to 10 working days; adoption and surrogacy leave introduced; "
                     "sick leave increased to 12 days; Earned Leave carry-forward cap raised to 45 days; compassionate "
                     "leave introduced."),
            ("h", "1. Scope"),
            ("p", "Applies to all permanent associates of Kohler India Corporation Private Limited. Statutory entitlements "
                  "under the Maternity Benefit Act 1961 (as amended 2017), the Factories Act 1948 and applicable state Shops "
                  "and Establishments Acts are minimums; where this policy is more generous, the policy applies."),
            ("h", "2. Leave entitlements"),
            ("t", ["Leave type", "Entitlement", "Conditions"], [
                ["Earned Leave (EL)", "18 working days per calendar year", "Accrues 1.5 days/month; may be taken after 3 months of service"],
                ["Casual Leave (CL)", "8 days per year", "Maximum 3 consecutive days; not carried forward"],
                ["Sick Leave (SL)", "<b>12 days</b> per year", "Medical certificate required beyond 2 consecutive days"],
                ["Maternity Leave", "26 weeks paid (first two children); 12 weeks thereafter", "Per Maternity Benefit Act; up to 8 weeks may be taken before the expected date"],
                ["Paternity Leave", "<b>10 working days</b> paid", "Within 90 days of the birth; may be split into two blocks"],
                ["Adoption / Surrogacy Leave", "<b>12 weeks</b> paid for the primary caregiver; 10 working days for the secondary caregiver", "Child under 12 months at placement"],
                ["Compassionate Leave", "5 days", "Serious illness of immediate family; manager discretion"],
                ["Bereavement Leave", "3 days", "Immediate family"],
                ["Public Holidays", "10 per year per site calendar", "Includes 3 national holidays"],
            ]),
            ("h", "3. Carry-forward and encashment"),
            ("p", "Unused Earned Leave may be carried forward up to a maximum accumulation of <b>45 days</b>. Balances above "
                  "45 days lapse on 31 December. Earned Leave is encashed at basic salary on separation. Associates may "
                  "additionally encash up to 5 days of Earned Leave once per year while in service."),
            ("h", "4. Application and approval"),
            ("p", "Leave is applied in Workday at least 7 days in advance (Earned Leave) or as soon as practicable (Sick and "
                  "Casual Leave). Managers respond within 2 working days. Leave during the quarter-end close (last 5 working "
                  "days of March, June, September and December) requires second-level approval for Finance associates."),
            ("h", "5. Questions"),
            ("p", "Contact HR India at hr.india@kohler.example or the People Services portal."),
        ],
    ),

    # ───────────────────────── H5 Remote & Hybrid Work ─────────────────────────
    dict(
        id="hr_remote_hybrid_work", doc_code="HR-GL-004", format="docx",
        title="Remote and Hybrid Work Policy", domain="hr", region="global",
        audience="internal", sensitivity="internal", owner="Global Human Resources",
        version="1.3", effective_date="2024-09-01", policy_key="hr.remote_work",
        tags=["hr", "remote-work", "hybrid", "flexible-work"],
        path="hr/global/remote_hybrid_work_policy_v1.3.docx",
        blocks=[
            ("h", "1. Work patterns"),
            ("t", ["Pattern", "Definition", "Eligibility"], [
                ["On-site", "5 days per week at a Company location", "Manufacturing, showroom, laboratory and site-based roles"],
                ["Hybrid", "Minimum 3 days per week on site (anchor days set by the team)", "Office-based roles, by default"],
                ["Remote", "Fewer than 3 days per month on site", "Approved on a role-by-role basis; requires VP approval"],
            ]),
            ("h", "2. Principles"),
            ("b", ["Work location does not change job grade, pay range or performance expectations.",
                   "Core collaboration hours are 10:00–15:00 local time on working days.",
                   "Cross-border remote work (working from a country other than the employing entity's) is not permitted "
                   "without Legal and Tax approval, and is limited to 20 working days per year.",
                   "Associates must work from a location where Company data can be protected: no public or shared screens "
                   "for restricted information; VPN required for internal systems."]),
            ("h", "3. Equipment and expenses"),
            ("p", "The Company provides a laptop, headset and monitor. A one-time home-office allowance of USD 300 (INR "
                  "20,000 in India) is reimbursable against receipts through the expense system. Ongoing internet and "
                  "electricity costs are not reimbursed except where required by local law."),
            ("h", "4. Approval and review"),
            ("p", "Hybrid patterns are agreed between associate and manager and recorded in Workday. Remote arrangements are "
                  "reviewed every 12 months and may be withdrawn with 60 days' notice if business needs change."),
        ],
    ),

    # ───────────────────────── H6 Performance & Promotion (restricted) ─────────────────────────
    dict(
        id="hr_performance_promotion", doc_code="HR-GL-005", format="pdf",
        title="Performance Review and Promotion Guidelines", domain="hr", region="global",
        audience="internal", sensitivity="restricted", owner="Talent Management",
        version="4.0", effective_date="2025-01-01", policy_key="hr.performance_promotion",
        tags=["hr", "performance", "promotion", "calibration", "manager-only"],
        path="hr/global/performance_promotion_guidelines_v4.0_RESTRICTED.pdf",
        blocks=[
            ("note", "RESTRICTED — for people managers and HR only. Do not share ratings distributions or calibration "
                     "outcomes with associates."),
            ("h", "1. Review cycle"),
            ("p", "Goal setting in January; mid-year check-in in July; year-end review in November; calibration in early "
                  "December; ratings and pay decisions communicated in the first week of February."),
            ("h", "2. Rating scale and expected distribution"),
            ("t", ["Rating", "Definition", "Guideline distribution"], [
                ["5 — Exceptional", "Consistently exceeds all objectives; role-model behaviours", "5–10%"],
                ["4 — Exceeds", "Exceeds most objectives", "20–25%"],
                ["3 — Achieves", "Meets all objectives", "55–65%"],
                ["2 — Partially achieves", "Meets some objectives; development plan required", "5–10%"],
                ["1 — Does not achieve", "Performance improvement plan (PIP) required", "0–3%"],
            ]),
            ("h", "3. Merit increase matrix (FY26 budget: 4.0% global, 8.5% India)"),
            ("t", ["Rating", "Below range midpoint", "At midpoint", "Above midpoint"], [
                ["5", "8–10% (IN: 14–16%)", "6–8% (IN: 12–14%)", "4–6% (IN: 10–12%)"],
                ["4", "5–7% (IN: 10–12%)", "4–5% (IN: 9–10%)", "3–4% (IN: 8–9%)"],
                ["3", "3–4% (IN: 8–9%)", "3% (IN: 8%)", "2–3% (IN: 6–8%)"],
                ["2", "0–2% (IN: 0–4%)", "0%", "0%"],
                ["1", "0%", "0%", "0%"],
            ]),
            ("h", "4. Promotion criteria"),
            ("b", ["Minimum 18 months in current grade (12 months for grades 1–3).",
                   "Rating of 4 or 5 in the most recent cycle and at least 3 in the prior cycle.",
                   "Demonstrated performance at the next grade for at least two quarters, evidenced in the promotion case.",
                   "Approved headcount and budget; promotions above grade 9 require Business Unit President sign-off.",
                   "Promotion increase: to the greater of 8% (IN: 12%) or the minimum of the new range."]),
            ("h", "5. Calibration"),
            ("p", "Calibration sessions are chaired by HR Business Partners. Managers present evidence, not adjectives. "
                  "Outcomes are final once approved by the function head; changes after calibration require HR VP approval."),
        ],
    ),

    # ───────────────────────── H7 Compensation Bands (restricted, xlsx) ─────────────────────────
    dict(
        id="hr_compensation_bands_fy26", doc_code="HR-GL-006", format="xlsx",
        title="Compensation Bands FY26 — India and Global Reference", domain="hr", region="global",
        audience="internal", sensitivity="restricted", owner="Total Rewards",
        version="FY26", effective_date="2025-04-01", policy_key="hr.compensation_bands",
        tags=["hr", "compensation", "salary-bands", "manager-only"],
        path="hr/global/compensation_bands_fy26_RESTRICTED.xlsx",
        description=["Annual base salary ranges by grade. India figures in INR lakhs per annum (LPA); the USD sheet is the global reference band used for other markets.",
                     "Ranges are for people managers and Total Rewards only. Offers above the range maximum require Total Rewards approval.",
                     "All values are invented for the prototype."],
        sheets=[
            ("India_INR_LPA", ["Grade", "Title band", "Example roles", "Min (LPA)", "Mid (LPA)", "Max (LPA)", "Location differential"], [
                ["G3", "Associate", "Customer Care Executive, Junior Engineer", 4.5, 6.0, 7.5, "Gurugram/Pune +0%; Jhagadia plant −5%"],
                ["G4", "Senior Associate", "Support Specialist, Engineer", 6.5, 8.5, 10.5, "Same"],
                ["G5", "Specialist", "Senior Engineer, Analyst", 9.0, 12.0, 15.0, "Same"],
                ["G6", "Lead", "Team Lead, Senior Analyst", 13.0, 17.0, 21.0, "Same"],
                ["G7", "Manager", "Manager — Engineering / Finance / HR", 18.0, 24.0, 30.0, "Same"],
                ["G8", "Senior Manager", "Senior Manager", 26.0, 34.0, 42.0, "Same"],
                ["G9", "Director", "Director", 38.0, 50.0, 62.0, "Same"],
                ["G10", "Senior Director / VP", "Business Head", 55.0, 75.0, 95.0, "Same"],
            ], [8, 20, 40, 10, 10, 10, 34]),
            ("Global_USD_reference", ["Grade", "Title band", "Example roles", "Min (USD)", "Mid (USD)", "Max (USD)", "Geo zone"], [
                ["G3", "Associate", "Customer Care Representative", 42000, 52000, 62000, "Zone 2 (Kohler, WI) baseline"],
                ["G4", "Senior Associate", "Support Specialist, Engineer I", 55000, 68000, 81000, "Zone 1 (CA, NY) +12%"],
                ["G5", "Specialist", "Engineer II, Analyst", 70000, 87000, 104000, "Zone 3 (remote, low-cost) −6%"],
                ["G6", "Lead", "Senior Engineer, Team Lead", 88000, 110000, 132000, ""],
                ["G7", "Manager", "Manager", 105000, 130000, 155000, ""],
                ["G8", "Senior Manager", "Senior Manager", 130000, 160000, 190000, ""],
                ["G9", "Director", "Director", 165000, 205000, 245000, ""],
                ["G10", "Senior Director / VP", "Vice President", 210000, 265000, 320000, ""],
            ], [8, 20, 36, 12, 12, 12, 34]),
            ("Rules", ["Rule", "Detail"], [
                ["Range penetration", "New hires are normally offered between minimum and midpoint."],
                ["Above-max", "Requires Total Rewards approval; lump-sum in lieu of increase if already above max."],
                ["Promotion increase", "Greater of 8% (IN: 12%) or the new range minimum — see HR-GL-005."],
                ["Confidentiality", "Restricted. Never disclose ranges to candidates or associates except as required by law (e.g. pay-transparency states)."],
            ], [24, 100]),
        ],
    ),
]
