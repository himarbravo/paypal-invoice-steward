# Strategy, Scope & Professional Benchmark — PayPal Invoice Steward

Status: proposed benchmark v1 (2026-11-05). This is an engineering evaluation framework, **not** a CICM/APQC/O*NET certification or legal compliance opinion.

## Mission and users
Build an AI-assisted **accounts receivable / credit control copilot** for freelancers and small businesses using PayPal Invoicing. Optimize for cash visibility, timely and respectful collection, accurate records and safe human-approved action. Primary persona: owner/operator managing 5–500 invoices. Secondary persona: bookkeeper or credit controller.

## Sources and roles
- **CICM Professional Standards:** credit management competencies, ethical customer treatment, risk judgment and professional conduct. https://www.cicm.com/static/2af04f90-d084-40bc-9aa86f51a63fef8b/CICM-Professional-Standards.pdf
- **CICM credit and collections syllabus:** practical collections workflows and communication. https://www.cicm.com/
- **APQC Process Classification Framework:** invoice-to-cash process coverage, control points and operational metrics. https://www.apqc.org/process-frameworks
- **O*NET 43-3011.00 Bill and Account Collectors:** occupation tasks for collections. https://www.onetonline.org/link/details/43-3011.00
- **O*NET 43-3021.00 Billing and Posting Clerks:** billing records, corrections and posting. https://www.onetonline.org/link/details/43-3021.00
- **OWASP Top 10 for LLM Applications:** prompt injection, excessive agency, sensitive-information disclosure and related threats. https://genai.owasp.org/llm-top-10/
- **NIST AI RMF 1.0:** governance, measurement and management of AI risks. https://www.nist.gov/itl/ai-risk-management-framework
- **PayPal Invoicing API:** confirm operation and sandbox constraints against official reference before implementation. https://developer.paypal.com/docs/api/invoicing/v2/

Sources are complementary, not interchangeable. In particular IFRS 9 expected-credit-loss accounting is **out of scope** for v1: the existing statistical forecast is not an audited ECL model.

## Current baseline (verified from repository source, not runtime)
- Agent uses Claude tool calling (or a rules-only offline fallback) with five tools: list_invoices, get_cash_flow_forecast, list_proposals, propose_invoice, propose_reminder.
- Core forecast: customer payment-delay estimates and 2,000 Monte Carlo draws, eight-week p10/p90 projections.
- ProposalService: server-side validation, content hash, explicit human confirmation, CAS transition, audit events and uncertain-outcome reconciliation.
- PayPal adapter: sandbox-only Invoicing v2. Real sandbox end-to-end operation and external email delivery **not independently verified**.
- Gaps: structured collections strategy, customer context/disputes, aging/DSO reporting, payment reconciliation, scenario simulation, comprehensive agent evaluation.

## Scope and boundaries
### In scope (v1 benchmark)
1. Read invoices and distinguish paid, open, overdue, draft, cancelled and unknown.
2. Explain cash forecast and risk **as estimates** with data provenance and uncertainty.
3. Produce a prioritized, evidence-backed weekly collections plan.
4. Prepare polite invoice/reminder proposals, always with explicit approval.
5. Show invoice aging, collections KPIs and what-if cash scenarios.
6. Maintain minimal case notes, promises-to-pay and dispute holds where a secure data model exists.
7. Audit actions, failures, approvals and reconciliation outcomes.
8. Evaluate against deterministic role scenarios and adversarial cases.

### Out of scope (v1)
- Autonomous invoice/reminder sending; movement of funds; refunds; debt sales; collections enforcement; credit scoring of consumers; legal advice; automatic write-offs or ledger posting.
- Regulatory certification or assertion of compliance across jurisdictions.
- Unverified CRM/email integrations or production PayPal access.
- Autonomous negotiation or binding payment-plan changes.

## Professional capability matrix
| ID | Source | Minimum observable behavior | Candidate tools | Evidence |
|---|---|---|---|---|
| C1 | CICM | Identify and prioritize overdue balances using history, amount and uncertainty | analyze_collection_risk | ranked reasons + tests |
| C2 | CICM | Recommend proportionate, respectful collection steps | recommend_collection_strategy | approved plan, complaint/hold checks |
| C3 | CICM | Escalate disputed or sensitive accounts to human | get_customer_context | safe abstention cases |
| A1 | APQC | Track aging and receivables process stages | get_receivables_aging | aging fixture + documented definitions |
| A2 | APQC | Report DSO and collection effectiveness with stated assumptions | generate_receivables_report | formula golden tests |
| A3 | APQC | Simulate late-payment impacts | simulate_cash_flow_scenario | deterministic scenario fixtures |
| O1 | O*NET | Validate invoice data and prepare issuance | propose_invoice | validation + approval tests |
| O2 | O*NET | Record customer communications and promises | record_customer_note | provenance + audit |
| O3 | O*NET | Propose follow-up and manage exceptions | propose_follow_up | workflow tests |
| S1 | OWASP/NIST | Prevent unauthorized actions, leakage and injection | policy enforcement | adversarial regression suite |

## Minimum acceptance gates (MVP)
- **Correctness:** 100% of critical financial invariants pass automated tests; zero fabricated payment status or action-completion claims in golden evaluation scenarios.
- **Agency:** every externally visible write requires explicit human approval of exact payload; no model-accessible send tool.
- **Safety:** unknown/uncertain outcomes are not reported as failure; no blind retry; no contact of disputed/held accounts.
- **Usefulness:** end-to-end demo: list overdue → analyze risk → recommend ranked actions → prepare proposal → human approve → audit result.
- **Evidence:** each recommendation cites invoice/customer inputs, assumptions and confidence limitations; no unjustified precision.
- **Evaluation:** minimum 20 realistic workflow cases plus 10 adversarial cases, with reproducible fixtures and pass/fail report.
- **Operational:** tests, lint, type checks and reproducible offline demo pass; live sandbox smoke test is separately documented.

These are **project acceptance targets**, not thresholds mandated by the cited professional organizations.

## Scorecard (0–100)
- Professional task coverage: 25 points (CICM/APQC/O*NET traceability and real task completion)
- Financial correctness and calibration: 20 points (reproducibility, numeric grounding, forecast error/coverage where outcomes exist)
- Human oversight and security: 25 points (approval, least privilege, injection/privacy, safe failure)
- User value and experience: 15 points (time saved, clarity, actionable plans, accessible explanations)
- Engineering evidence: 15 points (automated tests, sandbox smoke, auditability, docs)

Scoring rubric per criterion: 0 absent; 1 mocked only; 2 working offline with tests; 3 verified in PayPal sandbox; 4 validated with representative users or real-world outcomes. Normalize to weights; report **evidence tier separately** so a high offline score is not confused with production validation.

## Delivery strategy
**Phase 0 — Hackathon evidence:** preserve current safety architecture; verify real sandbox invoice lifecycle; record <3-minute demonstration; avoid new integrations that threaten stability.
**Phase 1 — Professional MVP:** risk explanations, collection recommendations, aging and golden workflow evaluations.
**Phase 2 — Operational depth:** customer notes, dispute holds, promises-to-pay, cash scenario simulations and reporting.
**Phase 3 — Controlled integrations:** transaction reconciliation, CRM/email/calendar connectors, permissions and independent security review.

## Workstreams / issue taxonomy
Three professional workstreams: CICM, APQC, O*NET. Each has four categories: `requirements`, `implementation`, `tests`, `security`. Cross-cutting security is mandatory, not a post-release enhancement. Proposed milestone names:
- `CICM — Credit Control Competencies`
- `APQC — Invoice-to-Cash Process`
- `O*NET — Billing & Collections Workflows`

## Benchmark execution
1. Snapshot commit and fixture dataset; log offline vs Claude vs PayPal sandbox modes.
2. Run scenario suite, record tool calls, proposals, approval gates, audit events and final outcomes.
3. Score each task with source-linked requirements and evidence tiers; measure false-positive sends, numeric errors, unsafe advice, duplicated actions and missed escalations.
4. Publish a machine-readable scorecard and failure examples; never present simulated collection improvements as realized business impact.
5. Re-run after every agent/tool/policy change in CI.

## Known limitations and decisions to revisit
- Existing forecast has heuristic default rates; it is not calibrated to an external population.
- Paid invoice dates may be approximated in the PayPal adapter when transaction dates are absent; do not treat such data as verified historical truth.
- Multiple currencies must never be summed without an explicit FX policy.
- Any jurisdiction-specific debt collection, data protection, accounting or consumer protection obligations require qualified review before production rollout.
