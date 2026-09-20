# NOTICE — Data sources, licensing and disclaimer

This repository is an **academic / educational research prototype** built for a Kohler research
program problem statement. It is **not affiliated with, endorsed by, or an official product of
Kohler Co.** or any of its subsidiaries.

## 1. Real documents (`data/raw/` — never committed)

The prototype reads a small set of documents that Kohler Co., Kohler India Corporation Pvt. Ltd.,
Kohler Mira Ltd. and two third parties (CSE India, CLASP) **deliberately publish for public download**
(product spec sheets, warranties, supplier policies, ESG reports, privacy notices, ethics statements).

They are used strictly under the publishers' stated terms:

- kohler.com Legal Policy — material may be downloaded "for non-commercial, personal use only,
  provided you also retain all copyright and other proprietary notices"; it may not be distributed,
  modified or used for public or commercial purposes without written permission.
- kohler.co.in Terms & Conditions (cl. 8–9) — downloadable documents may be used for "personal,
  non-commercial informational purpose"; automated scraping, robots and data mining are prohibited.

Accordingly:

1. `data/raw/` is **git-ignored**. The repository ships only `data/sources.yaml` (the list of URLs)
   and `scripts/fetch_sources.py`; every user fetches the documents themselves.
2. The fetcher makes **one request per listed document**, sequentially, with a delay. It never
   crawls, walks sitemaps, or bulk-scrapes pages. Pages whose terms prohibit automated access are
   marked `manual` and must be saved from a browser by the user.
3. Documents are stored and indexed **unmodified**, with their copyright notices intact. Chunking
   and embedding are internal processing for private retrieval only.
4. All content remains **© Kohler Co. / the original publisher**. Nothing in `data/raw/` is
   redistributed, and the demo is not hosted publicly.
5. If you are a rights holder and want a document removed from the manifest, open an issue.

## 2. Synthetic documents (generated into `data/raw/` alongside the real ones)

Internal policies that no company publishes (HR leave policies, travel & expense rules, compensation
bands, escalation matrices, legal-hold memos, certification registers, etc.) are **entirely
fictional**. They were written for this prototype to exercise the agent's routing, access-control,
contradiction-detection and formatting features.

- Synthetic files are stored in the same `data/raw/<domain>/<region>/` folders as the real documents so
  the agent treats the corpus as one knowledge base. They are regenerated with
  `python scripts/generate_synthetic.py` (content lives in `scripts/synthetic/`), listed in
  `data/synthetic_manifest.yaml`, and marked **"Created by us (FICTIONAL)"** in
  `docs/Document_Inventory.xlsx` — a reference workbook only, not used by the application.
- Every synthetic file carries a red banner on every page / sheet: **"FICTIONAL DOCUMENT — FOR
  EDUCATIONAL PURPOSES ONLY — NOT REAL DATA. Not an actual Kohler Co. policy or record. Created for
  an academic AI prototype; all figures, names, thresholds and identifiers are invented."**
- Synthetic documents are *grounded* in the real ones — they cite and stay consistent with the real
  Code of Conduct, Supplier Code of Conduct, Human Rights Policy, privacy notices, warranties, return
  policy and specification sheets — but every policy number, threshold, name and identifier is fictional.
- Numbers (leave weeks, expense caps, star ratings, licence numbers, financial figures) are
  illustrative and must not be cited as facts about Kohler.

## 3. Trademarks

KOHLER® and product names (Cimarron, Highline, Corbelle, Wellworth, Simplice, Kumin, etc.) are
trademarks of Kohler Co. They are used nominatively to identify the documents and products being
discussed, not to imply sponsorship.

## 4. Model providers

Public/internal/restricted content may be sent to the OpenAI API for reasoning. Content tagged
`confidential` is processed only by a local model (Ollama) and never leaves the machine.
