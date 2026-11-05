# Professional benchmark — final source audit

**2026-11-05. Documentary validation only; no software or sandbox execution.**

## Primary sources checked

- CICM *Professional Standards* (2022), especially printed page 33, *Cash Collections*: https://www.cicm.com/static/2af04f90-d084-40bc-9aa86f51a63fef8b/CICM-Professional-Standards.pdf . The standards distinguish Affiliate, Associate, Member and Fellow; these membership grades are not interchangeable with qualification levels.
- APQC *What Is Order-to-Cash?*, *How Organizations Manage Order-to-Cash*: https://www.apqc.org/What-Is-Order-to-Cash . Nine stages include invoicing, receivables, collections, adjustments and cash application.
- APQC *How Should Order-to-Cash And Accounts-Receivable Performance Be Measured And Improved?*: https://www.apqc.org/How-Should-Order-to-Cash-And-Accounts-Receivable-Performance-Be-Measured-And-Improved . Identifies DSO, average days delinquent and balanced process measures.
- APQC *Process Frameworks*: https://www.apqc.org/process-frameworks . Current cross-industry PCF version **8.0**; exact numeric process identifiers **not independently extracted**.
- O*NET *Bill and Account Collectors*, 43-3011.00, updated 2026, *Tasks*: https://www.onetonline.org/link/summary/43-3011.00 .
- O*NET *Billing and Posting Clerks*, 43-3021.00, updated 2026, *Tasks*: https://www.onetonline.org/link/summary/43-3021.00 . Individual machine-readable task IDs were not verified; occupation codes and task text are verified.
- PayPal *Invoices v2*, invoice list/draft/send/remind/payment/refund operations: https://developer.paypal.com/api/invoicing/v2/ . Endpoint availability does not establish product implementation or permissions.
- OWASP *Top 10 for LLM Applications 2025*: https://genai.owasp.org/llm-top-10/ . **LLM01** prompt injection, **LLM02** sensitive information disclosure, **LLM06** excessive agency; older LLM08 labels must be version-qualified.
- NIST *AI RMF Core*, Measure and Manage: https://airc.nist.gov/airmf-resources/airmf/5-sec-core/ and MANAGE 1.1: https://airc.nist.gov/airmf-resources/playbook/manage/ . Voluntary AI risk guidance.

## Final disposition of all 30 capabilities

DIRECT means the business behavior appears in a primary source, not that a software implementation is mandated. DERIVED means the professional objective is supported but the implementation is a product interpretation. PRODUCT means independent engineering, safety or test policy.

| Capability | Classification | Disposition | Verified anchor |
|---|---|---|---|
| C01 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C02 | DIRECT | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C03 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C04 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C05 | DIRECT | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C06 | DIRECT | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C07 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C08 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |
| C09 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| C10 | DERIVED | Retain with classification | CICM 2022 Cash Collections p.33 and/or O*NET 43-3011.00 Tasks |
| A01 | DIRECT | Retain with classification | APQC O2C stages and performance measures |
| A02 | DERIVED | Retain with classification | APQC O2C stages and performance measures |
| A03 | DIRECT | Retain with classification | APQC O2C stages and performance measures |
| A04 | DERIVED | Retain with classification | APQC O2C stages and performance measures |
| A05 | DIRECT | Retain with classification | APQC O2C stages and performance measures |
| A06 | DIRECT | Retain with classification | APQC O2C stages and performance measures |
| A07 | DERIVED | Retain with classification | APQC O2C stages and performance measures |
| A08 | DERIVED | Retain with classification | APQC O2C stages and performance measures |
| A09 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |
| A10 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |
| O01 | DIRECT | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O02 | DIRECT | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O03 | DIRECT | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O04 | DIRECT | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O05 | DERIVED | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O06 | DIRECT | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O07 | DERIVED | Retain with classification | O*NET 43-3011.00 / 43-3021.00 Tasks |
| O08 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |
| O09 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |
| O10 | PRODUCT | Retain with classification | OWASP 2025 / NIST AI RMF where applicable; product-specific control |

## Corrections and residual limitations

1. CICM standards are human competencies across membership grades, not a software certification; do not attribute advanced management tasks to an entry-level operator.
2. APQC O2C is broader than this invoice-to-cash product. The full PCF 8.0 numeric taxonomy remains **unverified**; no numeric identifiers are invented.
3. O*NET occupational tasks are not an authorization to automate debtor tracing, repossession, disconnection or legal escalation. Stable task IDs remain **unverified**; use exact task descriptions.
4. PayPal recording an external payment is not equivalent to verifying PayPal-hosted settlement; refunds and credit notes are not equivalent.
5. Aging thresholds, contact cadence, exact-payload approval, multi-tenancy and adversarial test suites are product choices, not mandated by CICM/APQC/O*NET.
6. Exact source-version publication dates beyond the identified CICM 2022 and O*NET 2026 were not established. Source URLs are current access points, not immutable archival snapshots.

**Documentary audit verdict: COMPLETE WITH DISCLOSED SOURCE-GRANULARITY LIMITATIONS.** Every capability has a classification, an authoritative source family and a retain decision. No claim of implementation validation, legal compliance or professional certification.
