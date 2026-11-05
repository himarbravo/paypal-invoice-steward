# Second-pass skeptical source and backlog gap audit

**Date:** 2026-11-05. **Scope:** documentary source quality, source-to-requirement precision and GitHub issue completeness; **no implementation or tests performed**.

## Method and confidence

Re-read all existing professional capability issues **#41–70**, integration issues **#71–72**, and the benchmark strategy. Cross-checked focused official PayPal Invoicing v2, invoice lifecycle, webhooks, REST webhook authentication, APQC PCF 8.0 process identifiers and measure pages, and GDPR articles 5, 6 and 22. Prior source-family links attached to issues were often generic: **a URL to a reputable organization is not evidence that a specific feature is mandated**. Professional curriculum sections (CICM, IOFM), full accounting and jurisdictional applicability, PayPal sandbox operation and exhaustive API schemas were **not** independently revalidated.

**Verdict:** meaningful new gaps remain; **do not label the entire professional source audit closed**. No claim of exhaustive completeness.

## Critical findings (ranked)

| Severity | Gap | Source-level evidence | GitHub disposition |
|---|---|---|---|
| P0 | Merchant/app authorization, scopes, identity, revocation and tenant isolation | PayPal OAuth 2.0 and Invoicing scopes; GDPR data boundaries | **New #73** |
| P0 | Data lifecycle, lawful basis, controller/processor, model-provider transfers, retention, rectification, automated decision boundary | GDPR Articles 5, 6, 22 (conditional) | **New #74** |
| P0 | Invoice inventory completeness, pagination/backfill, freshness and conflict precedence | PayPal list/search/show; webhook app scoping | **New #75** |
| P0 | Webhook signature-verification examples **conflict across official pages** | REST guide uses CRC32/raw body and base64 signature or verification API; invoice-specific guide presents a different illustrative verifier | **Amended #71**; no verified implementation assumption |
| P0 | Merchant auto-reminders and scheduled invoices can bypass internal contact holds | PayPal v2 auto reminder configuration, cancel-reminders, future issue date | **Amended #72** |
| P0 | Financial status conflation: hosted vs externally marked paid/refunded, partial statuses | PayPal invoice lifecycle | **Amended #55**; also #66 |
| P1 | APQC process IDs incorrectly treated as metric definitions | APQC PCF 8.0 IDs vs measure IDs/formulas | **Amended #53** |
| P0 | Security standard does not substitute for privacy law | GDPR Articles 5/6/22; OWASP/NIST | **Amended #69**, new #74 |

## Primary official references and what they establish

1. **PayPal Invoicing v2:** https://developer.paypal.com/api/invoicing/v2/ — invoice endpoints, search, merchant automatic reminder settings, cancel-reminders and external payment/refund operations. An API's existence does not prove the app has permission or implements it.
2. **PayPal invoice lifecycle:** https://developer.paypal.com/invoicing/core-concepts/ — `DRAFT`, `SENT`, `PARTIALLY_PAID`, `PAID`, `MARKED_AS_PAID`, `REFUNDED`, `MARKED_AS_REFUNDED`, `PARTIALLY_REFUNDED`, `CANCELLED`; scheduled delivery can occur independently.
3. **PayPal Invoicing webhooks:** https://developer.paypal.com/api/invoicing/webhooks/ — invoice events; illustrative signature verification example requires cross-check.
4. **PayPal REST webhooks guide:** https://developer.paypal.com/api/rest/webhooks/rest/ and https://developer.paypal.com/api/rest/webhooks/ — verification API or CRC32/raw-body/base64 signature; app-scoped event delivery, retry behavior. Do not silently treat differing signing examples as equivalent.
5. **PayPal REST OAuth:** https://developer.paypal.com/api/rest/authentication — bearer tokens and scopes; this does **not** establish third-party merchant authorization for our particular integration.
6. **PayPal reminder operation:** https://developer.paypal.com/api/invoicing/v2/invoices-remind/ — provider states API caller can send only **2 reminders/day**; not a general ethical or statutory contact frequency.
7. **APQC PCF 8.0 public taxonomy:** https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/percentage-receipts-automatically — `9.2.3.1 (10799)`, `9.2.3.3 (10801)`, `9.2.3.4 (10802)`, `9.2.4.1 (10804)`, `9.2.4.2 (10805)`. This page also identifies **measure 102463** for automatically matched receipts. A **process identifier is not a metric identifier or formula**. Some public APQC process descriptions are broad and must not be mistaken for implementation instructions.
8. **EU GDPR official text:** https://eur-lex.europa.eu/eli/reg/2016/679/oj — Article 5 (principles), 6 (lawful basis), 22 (conditional solely automated decision safeguards). Applicability requires jurisdiction and processing-context analysis.

## Gaps assigned to existing issues rather than duplicates

- #41/#42: customer profiling and prioritization must identify the difference between heuristic collection priority and legally significant creditworthiness decisions; cross-reference #74.
- #43/#46/#49/#65: collection holds and contact policy need #72's external reminder visibility; no assertion that local hold stops PayPal.
- #51/#52/#55/#57/#58: finance outputs must carry #75's source coverage/freshness status and #71's event provenance; no claims of comprehensive AR from partial invoice access.
- #53: exact metric measure ID, formula, numerator, denominator, population and period are outstanding.
- #55/#56/#66: hosted/external payment and refund distinctions, partial payments and ledger provenance; accounting treatment still conditional.
- #61/#62/#69/#70: require #73 merchant authorization and #74 privacy processing boundaries.

## Explicitly not in current autonomous scope

- General-ledger posting, full ERP reconciliation, tax return generation or legally binding credit-note issuance **without a supported accounting system and jurisdiction-specific requirements**.
- Credit denial, collection agency handoff, litigation, debt tracing, debt enforcement, debt sale or repossession.
- Autonomous alteration of merchant-wide reminder configuration or unapproved customer communications.
- General consumer debt collection across jurisdictions, IFRS expected-credit-loss calculation for entities whose reporting framework is unknown.
- Unverified third-party PayPal OAuth/partner permissions; unsupported provider data is marked unavailable, not inferred.

These are **documented exclusions/deferred capabilities**, not gaps that must automatically become implementation tickets.

## Remaining audit gates (do not declare source validation complete)

1. Obtain exact CICM/NACM/IOFM clauses or publicly accessible curriculum sections for each B practice, recording edition, location and scope; proprietary training content cannot be presumed.
2. Verify APQC DSO/ADD/effectiveness **measure-level** IDs, formulas and denominators. Otherwise label formulas product-defined.
3. Audit PayPal endpoint schemas, pagination, rate limits, token scopes, webhook authenticity and partner/merchant onboarding **against the intended account model**, including sandbox observations later.
4. Define target launch jurisdictions, business vs consumer debt, invoicing entity and accounting regime before legal/accounting claims.
5. Run a final 35-issue issue-to-source matrix: source exact passage, applicability, behavior, negative behavior, owner, dependencies and evidence status.
6. Decide whether the hackathon demo is explicitly **single-merchant sandbox** or a genuine multi-merchant product. The latter materially increases authorization, privacy and tenancy obligations.

**Overall assessment:** current backlog is substantially stronger but remains **provisionally complete as a requirements inventory**, not validated for implementation, professional certification, legal compliance or production readiness.
