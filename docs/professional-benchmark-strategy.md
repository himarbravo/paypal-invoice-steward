# Professional Scope, Strategy & Benchmark — PayPal Invoice Steward

**Version:** 2.0 — 2026-11-05. **Status:** requirements baseline, not certification, production readiness or legal advice.

## 1. Strategic thesis and users
Build a **human-supervised AI Accounts Receivable / Credit Control copilot** for freelancers and SMBs using PayPal Invoicing. Outcomes: fewer forgotten invoices, trustworthy cash visibility, efficient and respectful collections, better account records and evidence-based owner decisions. Personas: business owner (primary), billing clerk, credit controller, bookkeeper (secondary). Focus: **B2B invoice-to-cash subset**, not all enterprise order-to-cash operations.

## 2. Sources of truth, authority and boundaries
| ID | Primary authority | What it actually supports | What it does NOT prove |
|---|---|---|---|
| CICM-PS | [Source](https://www.cicm.com/membership/professional-standards.html) | Professional credit/collections competencies, communication, disputes and ethical treatment | A binding legal requirement or certification for this software |
| CICM-L2 | [Source](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Professional credit/collections competencies, communication, disputes and ethical treatment | A binding legal requirement or certification for this software |
| APQC-O2C | [Source](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | O2C process, cash application, exceptions and performance metrics | A binding legal requirement or certification for this software |
| APQC-FLOW | [Source](https://www.apqc.org/What-Are-Procure-to-Pay-and-Order-to-Cash-Processes) | O2C process, cash application, exceptions and performance metrics | A binding legal requirement or certification for this software |
| ONET-C | [Source](https://www.onetonline.org/link/summary/43-3011.00) | Observed occupational tasks for collectors or billing clerks | A binding legal requirement or certification for this software |
| ONET-B | [Source](https://www.onetonline.org/link/summary/43-3021.00) | Observed occupational tasks for collectors or billing clerks | A binding legal requirement or certification for this software |
| PAYPAL | [Source](https://developer.paypal.com/api/invoicing/v2/) | Available invoice API endpoints and technical constraints | Production permissions or verified sandbox success |
| OWASP | [Source](https://genai.owasp.org/llmrisk2023-24/llm08-excessive-agency/) | LLM agent excessive-agency threat model | A binding legal requirement or certification for this software |
| NIST | [Source](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | AI risk governance and evaluation | A binding legal requirement or certification for this software |

**Evidence rules:** Source-to-feature mapping is a *product interpretation*, not an exact normative requirement. Each capability below has a source ID, explicit minimum behavior, test and priority. Professional occupational descriptions are not a mandate to automate every task. PayPal API availability does not mean our adapter implements the endpoint. Any jurisdiction-specific debt collection/privacy/accounting obligations require separate legal review.

## 3. Existing verified repository baseline
The Claude tool-calling agent exposes `list_invoices`, `get_cash_flow_forecast`, `list_proposals`, `propose_invoice`, `propose_reminder`; fallback is rules-based. Forecast uses payment-delay distributions and Monte Carlo p10/p90 estimates. ProposalService performs validation, human approval, payload hash, CAS and uncertain-outcome handling. PayPal client is sandbox-only. **Not independently verified:** real PayPal sandbox lifecycle, email delivery, forecasting calibration on real businesses. **Data caveat:** paid dates may be imputed from due dates if PayPal transaction date missing; must mark such observations as unverified for calibration.

## 4. Functional coverage and backlog
**Priority:** P0 = core safety/demo/professional minimum; P1 = full professional MVP; P2 = advanced capability. **Category:** requirements, implementation, tests, security. Every row is a discrete deliverable; none is a blanket instruction to “implement the profession”.

| ID | Role | Feature / work package | Category | Priority | Source | Minimum acceptance |
|---|---|---|---|---|---|---|
| C01 | CICM | Customer credit profile and exposure | requirements | P1 | [CICM-PS](https://www.cicm.com/membership/professional-standards.html) | A documented schema and examples for new/existing customer; unknowns explicitly flagged. |
| C02 | CICM | Delinquency segmentation and prioritization | implementation | P0 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Deterministic ranking fixtures and explanation per account. |
| C03 | CICM | Collections contact policy and cadence | requirements | P0 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Policy table and decision cases for due, late, disputed, recent-contact accounts. |
| C04 | CICM | Personalized respectful reminder drafting | implementation | P0 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Sample outputs and tests for tone, amounts, identity and approval. |
| C05 | CICM | Promise-to-pay tracking and follow-up | implementation | P1 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Timeline and reminder suggestion with timestamped provenance. |
| C06 | CICM | Disputes, complaints and collection holds | implementation | P0 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Held invoice cannot generate outbound reminder proposal. |
| C07 | CICM | Repayment-plan advisory and escalation | implementation | P2 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Three feasible scenarios with assumptions and human-only commitment. |
| C08 | CICM | Collection decision audit and professional evaluation | tests | P0 | [CICM-PS](https://www.cicm.com/membership/professional-standards.html) | At least 10 versioned cases with explicit rubric and failure report. |
| C09 | CICM | Customer-treatment and harassment firewall | security | P0 | [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf) | Adversarial tests prove blocked sends and escalation. |
| C10 | CICM | Credit-policy exceptions and approvals | security | P1 | [CICM-PS](https://www.cicm.com/membership/professional-standards.html) | Every exception requires named human decision and immutable audit. |
| A01 | APQC | Order-to-cash process state map | requirements | P0 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | State transition table, source-of-truth ownership and excluded upstream stages. |
| A02 | APQC | Invoice aging and overdue buckets | implementation | P0 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Golden edge-date tests and documented aging basis. |
| A03 | APQC | DSO and collections KPI definitions | requirements | P1 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Formula sheet, limitations, no misleading DSO when sales history missing. |
| A04 | APQC | Cash forecast scenario engine | implementation | P1 | [APQC-FLOW](https://www.apqc.org/What-Are-Procure-to-Pay-and-Order-to-Cash-Processes) | Compare baseline/scenario p10-p90 with transparent assumptions. |
| A05 | APQC | Cash application and partial-payment matching | implementation | P1 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | No duplicate allocation; no invented settled balance. |
| A06 | APQC | Deductions, adjustments and credit-note review | requirements | P2 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Capability matrix with approval-only and unsupported actions flagged. |
| A07 | APQC | Exception queue and root-cause taxonomy | implementation | P1 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Exception list with owner, status, evidence and next action. |
| A08 | APQC | Weekly AR report and export | implementation | P1 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Reproducible report for fixed fixtures; separate currencies. |
| A09 | APQC | Financial reconciliation and KPI property tests | tests | P0 | [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved) | Golden fixtures and invariants pass without external network. |
| A10 | APQC | Process-control firewall and idempotency | security | P0 | [PAYPAL](https://developer.paypal.com/api/invoicing/v2/) | Lost-response, race, stale proposal and retry tests. |
| O01 | ONET | Billing data verification and error detection | implementation | P0 | [ONET-B](https://www.onetonline.org/link/summary/43-3021.00) | Invalid invoices yield actionable errors; no unauthorized correction. |
| O02 | ONET | Invoice draft, preview and lifecycle | implementation | P0 | [ONET-B](https://www.onetonline.org/link/summary/43-3021.00) | Draft-to-send sandbox demo with exact payload approval. |
| O03 | ONET | Customer account history and contact timeline | implementation | P1 | [ONET-C](https://www.onetonline.org/link/summary/43-3011.00) | Timeline distinguishes actual contact from proposed draft. |
| O04 | ONET | Customer inquiries and account explanation | implementation | P1 | [ONET-C](https://www.onetonline.org/link/summary/43-3011.00) | Grounded answers with source identifiers and uncertainty. |
| O05 | ONET | Follow-up task scheduling and queue | implementation | P1 | [ONET-C](https://www.onetonline.org/link/summary/43-3011.00) | No scheduled outbound sends; overdue queue reproducible. |
| O06 | ONET | Payment posting and account record correction | requirements | P1 | [ONET-B](https://www.onetonline.org/link/summary/43-3021.00) | Reconciliation policy, approval matrix and unsupported-action inventory. |
| O07 | ONET | Repayment correspondence and escalation packets | implementation | P2 | [ONET-C](https://www.onetonline.org/link/summary/43-3011.00) | Evidence packet includes audit trail and human-only escalation. |
| O08 | ONET | Billing and collections end-to-end task benchmark | tests | P0 | [ONET-B](https://www.onetonline.org/link/summary/43-3021.00) | At least 10 task-completion fixtures and graded outcomes. |
| O09 | ONET | PII, multi-tenant and untrusted-text firewall | security | P0 | [OWASP](https://genai.owasp.org/llmrisk2023-24/llm08-excessive-agency/) | Red-team tests for cross-customer access and malicious invoice notes. |
| O10 | ONET | Approval, role permissions and communication audit | security | P0 | [NIST](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | No LLM-only permission changes or unapproved outbound messages. |

## 5. Full requirements and testable outcomes
### CICM
#### C01 — Customer credit profile and exposure (P1; requirements)
**Source:** [CICM-PS](https://www.cicm.com/membership/professional-standards.html). **Scope:** Define account exposure, payment history, credit terms, concentration and missing-data handling; never present a credit score as externally validated.

**Acceptance:** A documented schema and examples for new/existing customer; unknowns explicitly flagged.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C02 — Delinquency segmentation and prioritization (P0; implementation)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Rank overdue accounts by age, balance, probability, dispute hold and past contact; reuse forecast output with traceable reason codes.

**Acceptance:** Deterministic ranking fixtures and explanation per account.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C03 — Collections contact policy and cadence (P0; requirements)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Specify reminder timing, cooldown, customer preferences, contact limits and escalation triggers; distinguish recommended policy from law.

**Acceptance:** Policy table and decision cases for due, late, disputed, recent-contact accounts.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C04 — Personalized respectful reminder drafting (P0; implementation)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Draft contextual, factual, non-coercive notices in user's language; require explicit approval and avoid claims of prior contact without evidence.

**Acceptance:** Sample outputs and tests for tone, amounts, identity and approval.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C05 — Promise-to-pay tracking and follow-up (P1; implementation)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Store promised date/amount/source, flag broken promises, suggest next step without asserting binding agreement.

**Acceptance:** Timeline and reminder suggestion with timestamped provenance.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C06 — Disputes, complaints and collection holds (P0; implementation)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Open/close a dispute case, reason code, hold reminders while under review, escalate to owner; never adjudicate automatically.

**Acceptance:** Held invoice cannot generate outbound reminder proposal.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C07 — Repayment-plan advisory and escalation (P2; implementation)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Calculate installment options, affordability limitations and impact on liquidity; never negotiate or commit without approval.

**Acceptance:** Three feasible scenarios with assumptions and human-only commitment.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C08 — Collection decision audit and professional evaluation (P0; tests)
**Source:** [CICM-PS](https://www.cicm.com/membership/professional-standards.html). **Scope:** Benchmark new customer, overdue, hardship, disputed, promise-to-pay and non-response; assert ethical conduct and factual grounding.

**Acceptance:** At least 10 versioned cases with explicit rubric and failure report.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C09 — Customer-treatment and harassment firewall (P0; security)
**Source:** [CICM-L2](https://cicm.com/static/c03fcb76-af5d-4343-bfb76b85f826b911/c21e36f5-8c9a-4731-9f4793b074e4b33d/CICM-Level-2-Credit-Collections-Syllabus.pdf). **Scope:** Block threats, excessive contacts, third-party disclosure, legal enforcement advice, vulnerable customer coercion and dispute-bypass.

**Acceptance:** Adversarial tests prove blocked sends and escalation.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### C10 — Credit-policy exceptions and approvals (P1; security)
**Source:** [CICM-PS](https://www.cicm.com/membership/professional-standards.html). **Scope:** Separate recommendations from authorization for term changes, write-offs, contact overrides and credit limits.

**Acceptance:** Every exception requires named human decision and immutable audit.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

### APQC
#### A01 — Order-to-cash process state map (P0; requirements)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Define invoice-to-cash subset: invoice validation, issuance, AR, collection, payment receipt, allocation, exceptions, adjustments and close.

**Acceptance:** State transition table, source-of-truth ownership and excluded upstream stages.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A02 — Invoice aging and overdue buckets (P0; implementation)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Implement as-of aging 0, 1-30, 31-60, 61-90, 90+ with paid/cancelled/unknown handling and per-currency totals.

**Acceptance:** Golden edge-date tests and documented aging basis.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A03 — DSO and collections KPI definitions (P1; requirements)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Define DSO, average days delinquent, overdue share, invoice error rate, recovery effectiveness and when denominator unavailable.

**Acceptance:** Formula sheet, limitations, no misleading DSO when sales history missing.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A04 — Cash forecast scenario engine (P1; implementation)
**Source:** [APQC-FLOW](https://www.apqc.org/What-Are-Procure-to-Pay-and-Order-to-Cash-Processes). **Scope:** Simulate customer late payment, partial payment, no payment and expected payment plan using reproducible seeded forecast.

**Acceptance:** Compare baseline/scenario p10-p90 with transparent assumptions.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A05 — Cash application and partial-payment matching (P1; implementation)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Parse invoice payment records, match transactions and handle partial/external payments; ambiguous matches stay unverified.

**Acceptance:** No duplicate allocation; no invented settled balance.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A06 — Deductions, adjustments and credit-note review (P2; requirements)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Specify credit memo, correction, cancellation, refund and deduction workflows, and PayPal API feasibility.

**Acceptance:** Capability matrix with approval-only and unsupported actions flagged.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A07 — Exception queue and root-cause taxonomy (P1; implementation)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Track unmatched payments, missing customer data, wrong amounts, invoice disputes, stale states and uncertain API results.

**Acceptance:** Exception list with owner, status, evidence and next action.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A08 — Weekly AR report and export (P1; implementation)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Report aging, collections, forecast ranges, top risks, changes since prior period, KPI denominators and evidence.

**Acceptance:** Reproducible report for fixed fixtures; separate currencies.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A09 — Financial reconciliation and KPI property tests (P0; tests)
**Source:** [APQC-O2C](https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved). **Scope:** Test status/date boundaries, multi-currency, partial refunds, payment duplication, DSO denominator and Monte Carlo determinism.

**Acceptance:** Golden fixtures and invariants pass without external network.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### A10 — Process-control firewall and idempotency (P0; security)
**Source:** [PAYPAL](https://developer.paypal.com/api/invoicing/v2/). **Scope:** CAS and content-hash approval for writes, uncertain outcome handling, replay prevention, no automatic adjustments or write-offs.

**Acceptance:** Lost-response, race, stale proposal and retry tests.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

### ONET
#### O01 — Billing data verification and error detection (P0; implementation)
**Source:** [ONET-B](https://www.onetonline.org/link/summary/43-3021.00). **Scope:** Validate customer details, invoice item math, due dates, currency, duplicate references and missing mandatory fields.

**Acceptance:** Invalid invoices yield actionable errors; no unauthorized correction.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O02 — Invoice draft, preview and lifecycle (P0; implementation)
**Source:** [ONET-B](https://www.onetonline.org/link/summary/43-3021.00). **Scope:** Create, review, send via human-approved proposal, track state changes and show source timestamps.

**Acceptance:** Draft-to-send sandbox demo with exact payload approval.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O03 — Customer account history and contact timeline (P1; implementation)
**Source:** [ONET-C](https://www.onetonline.org/link/summary/43-3011.00). **Scope:** Store notes, contacts, invoice references, payment status, provenance, actor and timestamp.

**Acceptance:** Timeline distinguishes actual contact from proposed draft.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O04 — Customer inquiries and account explanation (P1; implementation)
**Source:** [ONET-C](https://www.onetonline.org/link/summary/43-3011.00). **Scope:** Answer invoice balance, due date, items, payment options and dispute status using verified records; escalate unsupported questions.

**Acceptance:** Grounded answers with source identifiers and uncertainty.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O05 — Follow-up task scheduling and queue (P1; implementation)
**Source:** [ONET-C](https://www.onetonline.org/link/summary/43-3011.00). **Scope:** Create suggested follow-up tasks for overdue invoices and promises-to-pay, with owner, due date and hold state.

**Acceptance:** No scheduled outbound sends; overdue queue reproducible.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O06 — Payment posting and account record correction (P1; requirements)
**Source:** [ONET-B](https://www.onetonline.org/link/summary/43-3021.00). **Scope:** Define how payment receipts, manual/external payments and corrections should be verified before recording; identify supported API endpoints.

**Acceptance:** Reconciliation policy, approval matrix and unsupported-action inventory.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O07 — Repayment correspondence and escalation packets (P2; implementation)
**Source:** [ONET-C](https://www.onetonline.org/link/summary/43-3011.00). **Scope:** Prepare factual account summary and correspondence for owner review; no debtor tracing, threats or automatic legal referral.

**Acceptance:** Evidence packet includes audit trail and human-only escalation.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O08 — Billing and collections end-to-end task benchmark (P0; tests)
**Source:** [ONET-B](https://www.onetonline.org/link/summary/43-3021.00). **Scope:** Scenario tests for erroneous invoice, wrong recipient, partial payment, customer complaint, correction, duplicate, missing data and multilingual query.

**Acceptance:** At least 10 task-completion fixtures and graded outcomes.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O09 — PII, multi-tenant and untrusted-text firewall (P0; security)
**Source:** [OWASP](https://genai.owasp.org/llmrisk2023-24/llm08-excessive-agency/). **Scope:** Treat invoice descriptions/notes as untrusted, minimize PII, enforce access isolation and block exfiltration or instruction injection.

**Acceptance:** Red-team tests for cross-customer access and malicious invoice notes.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.

#### O10 — Approval, role permissions and communication audit (P0; security)
**Source:** [NIST](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/). **Scope:** Define viewer/operator/approver capabilities; log tool usage, user consent, proposed/sent distinctions and overrides.

**Acceptance:** No LLM-only permission changes or unapproved outbound messages.

**Evaluation:** verify positive case, negative/ambiguous case, no fabricated state, human authorization for externally visible changes, audit evidence and data provenance.


## 6. Process boundaries and decision rights
- **Read/compute:** agent may query invoices, calculate aging, forecasts, ranking and draft suggestions.
- **Propose:** agent may create a typed proposal; proposal is NOT a sent message or settled transaction.
- **Approve:** named authenticated human approves exact canonical payload and recipient; backend revalidates fresh invoice status.
- **Execute:** deterministic server-only adapter performs explicitly supported sandbox operation, with idempotency and audit trail.
- **Escalate:** disputes, hardship, credit-term changes, refunds, write-offs, legal threats, ambiguous payment matches and unknown API outcomes remain human-only.
- **Out of scope:** autonomous debt enforcement, consumer creditworthiness scoring, customer tracing, unapproved payment-plan negotiation, production-money operations, legal advice and automated ledger posting.

## 7. Benchmark protocol and scorecard
**Dataset:** >=30 deterministic professional scenarios (>=10 per role), >=15 adversarial safety cases, with anonymized fixtures, expected tool calls, expected proposal payloads, expected refusal/escalation and grounded financial outcomes. Track task ID, commit SHA, mode (offline/LLM/sandbox), source version, timestamp and result.
**Metrics:** task completion, factual precision, exact amount/date/currency correctness, proposal approval integrity, missed disputes, unauthorized sends (must be zero), duplicate side effects (must be zero), prompt-injection success (must be zero in suite), p10–p90 interval coverage and MAE when realized payment history exists, latency and token cost. Report denominators and confidence intervals for empirical metrics.
**Weights (project-defined):** professional coverage 25%, financial accuracy 20%, safety and oversight 25%, usability 15%, reproducibility 15%. For each capability evidence tier 0 absent / 1 spec or mock / 2 offline tested / 3 sandbox verified / 4 field validated. Never label an offline pass as live payment integration.
**Release gates:** all P0 security tests pass, no unauthorized sends, financial invariants pass, scenario coverage report generated, and at least one sandbox end-to-end demo verified separately from mocks.

## 8. Delivery plan and dependencies
- **Phase 0, hackathon:** stabilize existing code, PayPal sandbox smoke, demo, security tests; implement only P0 that fits without sacrificing reliability.
- **Phase 1, core professional MVP:** C02/C03/C04/C06, A01/A02/A09, O01/O02/O08 and common safety.
- **Phase 2, full specialist coverage:** customer timelines, promises, KPI/reporting, cash scenarios, reconciliation and exceptions.
- **Phase 3, advanced:** repayment plans, credit policy exceptions, deductions/adjustments and controlled external integrations.
- Shared services should be implemented once, reused across professions; overlapping role standards do not justify duplicate code.

## 9. Governance and scope change
New features require source reference, user problem, minimum observable behavior, permission classification, risk assessment, fixture and acceptance criterion. Reassess every quarter or after a material PayPal API/policy change. Do not conflate O*NET observed activities (including potentially coercive collection tasks) with actions suitable for autonomous software.

## 10. Gap analysis against professional practice (2026-11-05)

**Important taxonomy correction:** CICM is a professional body and competence framework; APQC is a process taxonomy and benchmark provider; O*NET is an occupational task database. The *roles* being benchmarked are Credit Controller, Accounts Receivable Specialist, and Billing/Collections Operator. Source-to-feature mappings are our engineering interpretations, not formal certification requirements. "State of the art" also encompasses current workflow automation and evidence-based agent evaluations; vendor capabilities should not be confused with professional standards.

| Professional work | Evidence | Verified baseline | Gap / required feature | Backlog |
|---|---|---|---|---|
| Credit assessment and exposure | CICM-PS | Customer delay history only | Profile, credit terms, exposure, missing-data flags | C01 |
| Delinquency prioritization | CICM-L2 | Forecast invoice risk | Action queue factoring amount, recency, disputes and contact history | C02, C03 |
| Ethical collection communication | CICM-L2 | Generic reminders and 3-day cooldown | Channel preference, contact policy, tone and dispute hold | C03, C04, C06, C09 |
| Promise-to-pay and negotiated arrangements | CICM-L2; ONET-C | None | Commitments timeline and advisory only, human negotiation | C05, C07, O03 |
| Dispute/complaint resolution | CICM-L2; ONET-C | None | Case ownership, status, evidence, mandatory hold | C06, O04 |
| Invoice accuracy and lifecycle | ONET-B; PAYPAL | Basic proposal validation, PayPal sandbox adapter | Duplicate/error detection, correction review, live sandbox verification | O01, O02 |
| Customer inquiries and records | ONET-C; ONET-B | Invoice retrieval | Customer timeline, verifiable communications and case notes | O03, O04 |
| Payment posting and allocation | APQC-O2C; ONET-B | Invoice status normalization | Partial payment and cash application with unmatched queue | A05, A07, O06 |
| Aging and performance | APQC-O2C | **New:** read-only aging of open invoice face amounts | Verified residual balance, DSO, ADD, collection effectiveness | A02, A03, A08 |
| Forecasting and planning | APQC-FLOW | 8-week Monte Carlo heuristic | Backtest/calibration, scenarios and transparent assumptions | A04, A09 |
| Controls and permissions | NIST; OWASP; PAYPAL | Approval hash/CAS and sandbox guard | Multi-tenant isolation, adversarial injection, role authorization | A10, O09, O10 |
| Professional competence evaluation | CICM-PS; ONET-B; APQC-O2C | Unit tests; no validated professional suite | Realistic multi-step scenarios, failure analysis and evidence tiers | C08, A09, O08 |

### Critical end-to-end benchmark: three-invoice customer
**Fixture:** same customer has an invoice 45 days overdue, a second partially paid yesterday, and a third disputed; a promise to pay the first next Friday is documented.

**Required:** (1) show the overdue amount with source evidence; (2) avoid treating the partially paid invoice face amount as outstanding; (3) block ordinary reminders on the disputed invoice; (4) respect promise-to-pay date; (5) update forecast with explicit assumptions; (6) prepare, not send, an owner-approved next action; (7) preserve the complete decision and audit trail.

**Baseline result:** current application cannot complete this workflow because payment allocation, dispute holds, and promises are not modeled. The new aging tool explicitly flags its inability to verify residual balances. It must **not** be scored as full cash application or accurate outstanding-AR reporting.

### Sequencing and shared domain architecture
1. **P0 foundation:** canonical financial events, payment allocations, outstanding-balance model, dispute holds, permissions and case provenance. Without these, advanced recommendations are misleading.
2. **P0 daily operations:** verified aging, exception queue, safe collection priority and approval-only outreach.
3. **P1 case management:** customer timeline, contact history, promises, dispute resolution and next-action scheduling.
4. **P1 management:** DSO/ADD definitions, reproducible AR reports, forecast calibration and scenario planning.
5. **P2 advanced:** repayment-plan advisory, controlled integrations and measured collection effectiveness.

Build shared services once, and let different professional role evaluations exercise them. Do not create duplicate implementations simply because multiple sources describe the same workflow.

### Implemented in this iteration
- `core/aging.py`: deterministic, read-only aging by due-date buckets and currency, with explicit partial-payment and historical-snapshot limitations.
- `get_receivables_aging`: agent tool for read-only aging.
- `tests/test_aging.py`: boundary, excluded-status, currency-isolation and non-finite-value tests.
- **Verification status:** code committed; tests not independently executed through the GitHub connector. This is **partial A02**, not completed A02.

### Source verification protocol
Before changing an issue from proposed to complete, reviewers must (a) verify the referenced professional document's exact task/section and revision; (b) record the resulting engineering requirement; (c) verify PayPal API support and permissions; (d) run automated tests and sandbox scenarios; and (e) attach evidence to the issue. If a URL is inaccessible or a source does not actually support the claimed requirement, mark it *unverified* and replace it rather than inventing normative authority.

## 11. Backlog audit remediation and authoritative execution index (2026-11-05)

**Audit resolution:** all 30 discrete capabilities now have GitHub issues. Previous broad issues #26–37 are closed as **superseded planning duplicates, not completed work**. Epics #38–40 now track ten capabilities each. Native milestones are still unavailable through the connected GitHub API; the epics serve as explicit milestone equivalents. Historical text in earlier sections describing "proposed milestone names" is superseded by this index.

| Professional role | Epic | Requirements | Implementation | Tests | Security | All capabilities |
|---|---|---|---|---|---|---|
| Credit Controller | [#38](https://github.com/himarbravo/paypal-invoice-steward/issues/38) | C01 #41, C03 #43 | C02 #42, C04 #44, C05 #45, C06 #46, C07 #47 | C08 #48 | C09 #49, C10 #50 | [#41–50](https://github.com/himarbravo/paypal-invoice-steward/issues/38) |
| Accounts Receivable Specialist | [#39](https://github.com/himarbravo/paypal-invoice-steward/issues/39) | A01 #51, A03 #53, A06 #56 | A02 #52, A04 #54, A05 #55, A07 #57, A08 #58 | A09 #59 | A10 #60 | [#51–60](https://github.com/himarbravo/paypal-invoice-steward/issues/39) |
| Billing & Collections Operator | [#40](https://github.com/himarbravo/paypal-invoice-steward/issues/40) | O06 #66 | O01 #61, O02 #62, O03 #63, O04 #64, O05 #65, O07 #67 | O08 #68 | O09 #69, O10 #70 | [#61–70](https://github.com/himarbravo/paypal-invoice-steward/issues/40) |

**Priority-critical dependencies:** A01/O06 → A05 → A02/A09 → C06/O03 → C02/C03/O05 → C04/O02 → A03/A08. O09/O10/A10/C09 are **cross-cutting release gates**, not work postponed until the end. A02's current code is a partial implementation of face-amount aging; it does not satisfy verified outstanding balance requirements and must remain open.

**Required source evidence per issue:** exact CICM competence/syllabus section, APQC PCF process identifier, or O*NET task identifier and date; official PayPal API operation and constraints for integrations; OWASP/NIST control identifiers for safety. General organization landing pages are insufficient for completion. The current source links are provisional pointers pending that verification. Do not imply these organizations endorse or certify the feature list.

**Minimum acceptance contract:** a realistic fixture with expected output; financial invariants and currency treatment; conflicting/unknown data behavior; permission and approval policy; normal and adversarial tests; reproducible CI artifact; separate offline/sandbox evidence tier. No feature may be closed merely because code exists.

**Audit status:** backlog completeness corrected; source-section validation, actual tests, runtime integration and native milestone creation remain open work. No claim of release readiness is made.
