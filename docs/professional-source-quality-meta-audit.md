# Independent audit of the benchmark's source quality

**Date:** 2026-11-05. **Scope:** suitability of authoritative references compared with professional credit-control, accounts-receivable and billing practice. Documentary review only.

## Finding: previous source audit was not sufficiently comprehensive

The original source set (CICM, APQC, O*NET, PayPal, NIST, OWASP) is reputable but mixes occupational descriptions, process frameworks, API documentation and AI security controls. It omitted specialized professional practice, financial reporting and jurisdiction-specific legal authorities. Its prior verdict of 'complete' should be read as 'initial mapping complete', **not** a completed professional-source selection audit.

## Comparative source suitability

| Source | Authority for | Limits | Decision |
|---|---|---|---|
| CICM Professional Standards and Level 2/3 syllabi | UK credit-control and collections competencies, professional conduct | Human competency grades are not technical specifications | Keep as primary role standard |
| APQC Cross-Industry PCF 8.0 and AR benchmarks | Process boundaries, AR operations, metrics, peer comparisons | Metrics require defined populations; many detailed datasets require membership | Keep as primary process standard; use actual PCF IDs |
| O*NET 43-3011.00 and 43-3021.00 | Descriptive occupational tasks | Does not prescribe correct accounting, credit policy or legal compliance | Retain as corroborating occupational evidence, not primary operations standard |
| NACM best credit and collection practices | B2B collection policies, contact, risk, exposure, holds, disputes, settlements | US-centric guidance; not law | **Add as primary practice reference** |
| IOFM ARS/ARM and AOCS curricula | Working AR and O2C competency domains: billing, cash application, disputes, controls | Public curriculum verifies coverage, not proprietary course content | **Add as professional training comparator** |
| IFRS 9 and IFRS 15 | Receivables recognition and credit-loss accounting where applicable | Accounting applicability depends on entity/reporting framework; ECL is not an operational cash forecast | **Add conditional accounting authority** |
| Applicable jurisdictional law (e.g., Spanish Ley 3/2004) | Payment deadlines, late interest and collection rights in covered transactions | Jurisdiction, customer type and transaction scope matter | **Add jurisdiction gate** |
| EDPB GDPR guidance | Personal-data processing in customer and debt collection workflows | Legal basis and proportionality are context-dependent | **Add privacy primary authority** |
| PayPal Invoicing v2 | Provider API capabilities | Not financial accounting or legal authority | Retain technical authority |
| OWASP LLM Top 10 / NIST AI RMF | Agent security and AI risk governance | Not AR professional standards | Retain technical/security authority |

## Verified stronger APQC traceability

Official APQC *Cross Industry (8.0)* measure-scope taxonomy publicly lists **9.2 Perform revenue accounting**, **9.2.1 Process customer credit**, **9.2.2 Invoice customer**, **9.2.3 Process accounts receivable**, **9.2.4 Manage and process collections**, and **9.2.5 Manage and process adjustments/deductions**. Specific identifiers include **10744** for AR, **10745** for collections, **10746** for adjustments, **10801** for apply cash remittances, and **10805** for analyze delinquent balances. These identifiers are **verified** and supersede the prior blanket statement that APQC identifiers were unavailable. Reference: https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/personnel-cost-perform-process-group-0 .

## Primary references newly evaluated

- NACM, *Best Credit and Collection Practices*: https://nacm.org/558-resources/best-credit-and-collection-practices.html .
- IOFM, *Accounts Receivable Certification*: https://www.iofm.com/certification/ar-certification/ .
- IOFM, *Order-to-Cash Specialist Certification*: https://www.iofm.com/certification/aocs .
- IFRS Foundation, *IFRS 9*: https://www.ifrs.org/issued-standards/list-of-standards/ifrs-9-financial-instruments/ .
- IFRS Foundation, *IFRS 15*: https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/ .
- Spain, *Ley 3/2004* (consolidated): https://www.boe.es/buscar/act.php?id=BOE-A-2004-21830 .
- EDPB, *Process personal data lawfully*: https://www.edpb.europa.eu/sme/be-compliant/process-personal-data-lawfully_en .
- CFPB, *Regulation F*: https://www.consumerfinance.gov/rules-policy/regulations/1006/ . Consumer-debt and covered debt-collector scope must not be extended to ordinary B2B invoices.

## Findings requiring correction in the 30-capability matrix

1. **C01/C02/C03/C06/C10:** Add NACM credit policy, exposure, dispute, hold and authorization practices as specific primary operational references.
2. **A01–A08:** Use APQC PCF 8.0 identifiers at process level; connect IOFM competency domains to billing, cash application, collections and disputes.
3. **A03:** Cite an exact APQC metric definition and denominator, not merely an APQC O2C article.
4. **A05/A06/O06:** Distinguish cash application, payment posting, refunds, credit notes and accounting adjustments using APQC, professional practice and applicable accounting guidance.
5. **C09/O09/O10:** Separate voluntary professional ethics, GDPR obligations, jurisdiction-specific debt-collection rules and AI security controls. Never imply US consumer-debt Regulation F automatically governs business debt or original creditors.
6. **O01–O08:** Keep O*NET for occupational corroboration; prioritize IOFM/APQC for operational practices.

## Quality verdict

**Original sources: credible, but insufficiently diverse for a professional operational benchmark.** The previous 30/30 'retain' classification was a *scope decision*, not proof that each capability had the strongest applicable professional source. The audit is **not closed at source-selection quality level** until the expanded references are attached at capability level and checked for jurisdiction, applicability, revision and exact cited section.

**No software testing or payment implementation is in scope for this audit.**
