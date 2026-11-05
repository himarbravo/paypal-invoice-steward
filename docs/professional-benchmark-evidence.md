# Professional benchmark: evidence validation register

**Validated against official public sources on 2026-11-05.** This is a **source-traceability validation**, NOT certification of software competence, legal compliance, or passing runtime tests. The 30 capability IDs refer to the existing [scope and strategy](professional-benchmark-strategy.md) and GitHub issues #41–70.

## Source authority and scope

1. **CICM Professional Standards (2022)** — [PDF](https://www.cicm.com/static/2af04f90-d084-40bc-9aa86f51a63fef8b/CICM-Professional-Standards.pdf), especially **Cash Collections, p.33**; professional standards describe human roles, not required agent features. **CICM Level 2** is the operational reference, Level 3 advanced and Level 5 managerial. [CICM Level 2 qualification](https://www.cicm.com/learning-development/qualifications/credit-and-collections/level-2.html) and [Credit Management syllabus topics](https://www.cicm.com/learning-development/qualifications/credit-and-collections/credit-management-trade-export-and-consumer.html).
2. **APQC** — [What Is Order-to-Cash](https://www.apqc.org/What-Is-Order-to-Cash), sections **How Organizations Manage Order-to-Cash** and **What are the most important O2C measures?**; APQC is a *process* authority, not an occupational credential. The public summary supports the process stages but does not establish our exact aging buckets or formulas.
3. **O*NET (2026)** — [Bill and Account Collectors 43-3011.00](https://www.onetonline.org/link/summary/43-3011.00) and [Billing and Posting Clerks 43-3021.00](https://www.onetonline.org/link/summary/43-3021.00), **Occupation-Specific Information → Tasks**. Occupation descriptions are not software automation mandates.
4. **PayPal Invoicing v2** — [official API reference](https://developer.paypal.com/api/invoicing/v2/), **Invoices** endpoint list. Supports draft/send/remind/show/update and recording external payments/refunds. API support does not establish authorization, adapter implementation or reconciliation completeness.
5. **Security** — [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) and [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/). Our explicit approval, role isolation and adversarial testing are engineering safety decisions; not requirements imposed by O*NET.

## Evidence classifications
- **DIRECT:** an identifiable source task/process/competency supports the business behavior. Implementation specifics remain ours.
- **DERIVED:** the source supports the business objective but the specific software feature or threshold is a product interpretation.
- **PRODUCT:** principally a software safety, test or UX decision; do not attribute it to an occupational standard.

## All 30 capabilities: evidence and validity

| ID | Evidence class | Specific source anchor and qualification |
|---|---|---|
| [C01](https://github.com/himarbravo/paypal-invoice-steward/issues/41) | **DIRECT** | CICM Credit Management (Trade Export Consumer), syllabus topic 4 Credit risk control |
| [C02](https://github.com/himarbravo/paypal-invoice-steward/issues/42) | **DIRECT** | CICM Professional Standards (2022), Cash Collections p.33; O*NET 43-3011.00 monitor overdue accounts |
| [C03](https://github.com/himarbravo/paypal-invoice-steward/issues/43) | **DERIVED** | CICM Professional Standards p.33, cash collections policy; contact cadence thresholds are product policy |
| [C04](https://github.com/himarbravo/paypal-invoice-steward/issues/44) | **DIRECT** | CICM Professional Standards p.33, proactive customer contact; O*NET 43-3011.00 notify customers |
| [C05](https://github.com/himarbravo/paypal-invoice-steward/issues/45) | **DIRECT** | CICM Professional Standards p.33, repayment plans and account records; O*NET 43-3011.00 repayment schedules |
| [C06](https://github.com/himarbravo/paypal-invoice-steward/issues/46) | **DIRECT** | CICM Professional Standards p.33, resolve account disputes and complaints |
| [C07](https://github.com/himarbravo/paypal-invoice-steward/issues/47) | **DERIVED** | CICM Professional Standards p.33, sustainable repayment plans; human-only advisory is product policy |
| [C08](https://github.com/himarbravo/paypal-invoice-steward/issues/48) | **PRODUCT** | CICM Professional Standards p.1 states professional development benchmark, not software testing |
| [C09](https://github.com/himarbravo/paypal-invoice-steward/issues/49) | **DERIVED** | CICM Professional Standards p.33, customer support and governance; detailed prohibited phrases/contact limits are product safety controls |
| [C10](https://github.com/himarbravo/paypal-invoice-steward/issues/50) | **DERIVED** | CICM Credit Management syllabus topic 2 Credit policy; exact approval workflow is product design |
| [A01](https://github.com/himarbravo/paypal-invoice-steward/issues/51) | **DIRECT** | APQC What Is Order-to-Cash, nine process components |
| [A02](https://github.com/himarbravo/paypal-invoice-steward/issues/52) | **DERIVED** | APQC What Is Order-to-Cash, AR and collections; specific aging bucket thresholds are product design |
| [A03](https://github.com/himarbravo/paypal-invoice-steward/issues/53) | **DIRECT** | APQC What Is Order-to-Cash, DSO and average days delinquent |
| [A04](https://github.com/himarbravo/paypal-invoice-steward/issues/54) | **DERIVED** | APQC What Is Order-to-Cash, cash forecasting support; scenario algorithm is product design |
| [A05](https://github.com/himarbravo/paypal-invoice-steward/issues/55) | **DIRECT** | APQC What Is Order-to-Cash, payment receipt and cash application; PayPal Invoicing v2 payment operations |
| [A06](https://github.com/himarbravo/paypal-invoice-steward/issues/56) | **DIRECT** | APQC What Is Order-to-Cash, adjustments and deductions; PayPal Invoicing v2 refunds and update operations |
| [A07](https://github.com/himarbravo/paypal-invoice-steward/issues/57) | **DERIVED** | APQC What Is Order-to-Cash, adjustments/deductions and cash application; queue taxonomy is product design |
| [A08](https://github.com/himarbravo/paypal-invoice-steward/issues/58) | **DERIVED** | APQC What Is Order-to-Cash, performance measures; weekly cadence/export are product choices |
| [A09](https://github.com/himarbravo/paypal-invoice-steward/issues/59) | **PRODUCT** | APQC process measurement requires reliable data; property-test suite is engineering policy |
| [A10](https://github.com/himarbravo/paypal-invoice-steward/issues/60) | **PRODUCT** | APQC process governance; PayPal Invoicing v2; exact idempotency/CAS controls are engineering policy |
| [O01](https://github.com/himarbravo/paypal-invoice-steward/issues/61) | **DIRECT** | O*NET 43-3021.00 task: Verify accuracy of billing data and revise any errors |
| [O02](https://github.com/himarbravo/paypal-invoice-steward/issues/62) | **DIRECT** | O*NET 43-3021.00 task: Prepare itemized statements, bills, or invoices; PayPal Invoicing v2 draft/send |
| [O03](https://github.com/himarbravo/paypal-invoice-steward/issues/63) | **DIRECT** | O*NET 43-3011.00 task: Record financial status and collection efforts |
| [O04](https://github.com/himarbravo/paypal-invoice-steward/issues/64) | **DIRECT** | O*NET 43-3011.00 task: Answer customer questions regarding problems with accounts |
| [O05](https://github.com/himarbravo/paypal-invoice-steward/issues/65) | **DERIVED** | O*NET 43-3011.00 task: Locate and monitor overdue accounts; scheduler/queue design is product choice |
| [O06](https://github.com/himarbravo/paypal-invoice-steward/issues/66) | **DIRECT** | O*NET 43-3011.00 task: Receive payments and post amounts; O*NET 43-3021.00 billing corrections |
| [O07](https://github.com/himarbravo/paypal-invoice-steward/issues/67) | **DERIVED** | O*NET 43-3011.00 tasks: Correspondence, repayment arrangements; human escalation is product safety |
| [O08](https://github.com/himarbravo/paypal-invoice-steward/issues/68) | **PRODUCT** | O*NET 43-3021.00 tasks list; automated benchmark harness is engineering policy |
| [O09](https://github.com/himarbravo/paypal-invoice-steward/issues/69) | **PRODUCT** | O*NET does not prescribe multi-tenant/LLM controls; OWASP LLM risk guidance is security authority |
| [O10](https://github.com/himarbravo/paypal-invoice-steward/issues/70) | **PRODUCT** | O*NET does not prescribe software roles; NIST AI RMF governance and PayPal operation constraints |

## Corrections to prior benchmark claims

- **Role taxonomy:** Credit Controller, AR Specialist, Billing & Collections Operator are product personas. CICM, APQC and O*NET are *different evidence types*, not three separate professional roles.
- **Qualification scope:** CICM Level 2 is operational; do not imply advanced credit underwriting or strategic management is mandatory for an entry-level invoice copilot.
- **Technical feasibility:** PayPal supports recording external payments and refunds, but these are state-changing financial records and must remain human-authorized. PayPal-hosted payments are distinct from external payments; never double-record them.
- **O*NET exclusions:** debtor tracing, repossession/disconnection and legal referrals are occupational tasks in some settings, but are explicitly **not** authorized agent functions.
- **Metric definitions:** DSO, aging, ADD and collection effectiveness require documented formulas, denominators and period/source assumptions. The source does not mandate our particular bucket thresholds or 30-case/15-adversarial test targets.
- **Safety:** the project-specific rules (cooldowns, exact-payload approval, CAS, prompt injection tests) are prudent controls, not CICM/APQC/O*NET certifications.
- **Financial accuracy:** existing aging of open invoice *face amounts* is not a verified outstanding-balance ledger for partial payments; no production financial claim until allocation tests and PayPal sandbox verification.

## Validation outcome and remaining gates

**PASS: source relevance and scope mapping.** All 30 capabilities have an explicit, publicly accessible primary source anchor or are correctly labeled as project-derived/product requirements. This does **not** mean all 30 are normative, fully specified or implemented.

**OPEN: evidence precision.** CICM p.33, named CICM syllabus topics, APQC named public sections and O*NET named tasks have been checked; stable individual O*NET task IDs and full APQC PCF numeric process identifiers are not yet verified. Do not invent them.

**OPEN: software validation.** For each capability, require scenario fixtures, expected financial outputs, adversarial/authorization cases, test run artifact, code commit and independent PayPal sandbox proof when applicable. Record source version/date and evidence tier. No issues should be closed based on this document alone.

**Verdict:** professional *scope is defensible as a proposed copilot benchmark*, with 12 direct/derived vs product distinctions shown individually above. The product is **not professionally certified**, and its implementation is **not yet validated**.
