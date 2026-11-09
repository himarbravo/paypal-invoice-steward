# Hackathon data flows and privacy boundaries

**Status: technical scope statement, NOT a GDPR compliance determination or legal advice.** Related issues: #74 (parent), #99 (sandbox LLM opt-in), #69/#95 (tool minimization), #73/#97 (PayPal credentials), #83 (release gate). The project supports one merchant's own **PayPal sandbox business account**, localhost-only, for a temporary hackathon demo.

## 1. Demo safety policy

- Use **synthetic customers, addresses and invoices only**. Never import a production merchant's customer list, correspondence or payment records into the sandbox, offline fixtures or Claude.
- The offline demo includes fictional customer fixtures. The real sandbox may contain whatever the operator entered; the application does **not** automatically classify invoices as synthetic.
- The sandbox starts **PayPal read-only**. Enabling sends requires `STEWARD_SANDBOX_WRITES=enabled` plus exact per-proposal human confirmation. No funds are collected or card credentials stored by this application.
- An Anthropic key in sandbox mode does **not** silently authorize external model processing. Startup fails unless `STEWARD_SANDBOX_LLM=enabled` is deliberately set. The opt-in acknowledges a data-flow risk for the **operator**; it is **not consent by any customer**, a contractual data-processing agreement or a legal basis under GDPR Article 6.
- The same operator's typed chat content may include names, email addresses or personal details. **Do not type real personal data** even when tool results are minimized.

## 2. Data flow inventory (as currently implemented)

| Source → destination | Data | Current safeguards | Open limitations |
|---|---|---|---|
| Merchant's sandbox → PayPal HTTPS API → app | Invoices, billing names/email, amounts, statuses and dates | Canonical sandbox origin, OAuth invoicing scope check and optional app-ID pin | Application ID does not prove merchant identity; full inventory/partial balances not verified (#73/#75) |
| Browser → localhost FastAPI | Operator chat, invoice requests, approval hashes, proposal IDs | Loopback request boundary; human confirmation for writes | No user login; reverse proxy/tunnel forbidden; operator chat is not automatically PII-redacted |
| App → Claude Messages API, only when model key provided | **Raw operator chat text** plus allowlisted numeric/opaque-ID invoice tool results, status and totals | Separate exact sandbox LLM opt-in; #95 model-only field projection omits raw customer names, emails and summaries | Identifiers and financial patterns may still be linkable personal data; no verified vendor retention/transfer contract; novel prompt-injection risk remains |
| App → local SQLite `STEWARD_DB` (default `data/steward.db`) | Proposal payloads, recipient emails, customer names, summaries, hashes, statuses, results, event/audit details | Local-only file, SQLite compare-and-swap execution and audit records | **No built-in retention schedule, per-person export or erasure**. Even redacted error logs do not imply the proposal database contains no PII |
| App → in-process Python memory | Invoice objects, recent LLM chat/tool history keyed by session ID, per-session labels that map invoice/proposal IDs to the invoice numbers/references shown in the UI (used to rewrite replies, never sent to the model), tokens | Per-session history trimmed to six user turns in `LLMAgent`; tokens never deliberately sent to LLM | Session dictionary has **no expiry or maximum session count**; data retained until process termination |
| App → local browser UI | Full invoice and proposal details for the person approving | Text is assigned through DOM text APIs, no direct HTML interpolation of invoice strings; localhost-only | In-browser visibility, screenshots, exports and browser/OS retention controlled by operator |
| App → logs/video/repository | Generic agent error category, application status, demo materials | #93 redacts upstream provider error text; `.env` is gitignored | Custom logs, screenshots, video and untracked files can still expose PII or secrets; must inspect before publication |

Data minimization of LLM tool results is **pseudonymization/limited disclosure, not guaranteed anonymization**. Invoice IDs and dates can identify someone when combined with another source.

The same local SQLite file also stores invoice-read timestamps, observed/missing invoice IDs and counts, partitioned by mode and a digest of the app client ID. This journal contains no added customer text or financial payloads; its IDs remain potentially linkable. It follows the same manual cleanup and retention limitations as proposals. No inventory journal is sent to the model.

Local contact holds store the invoice ID, controlled reason, active state, version and timestamp, plus set/release audit events. No dispute narrative or customer correspondence is collected. These records share the same local retention limitations; the app does not adjudicate a dispute or communicate a decision to PayPal.

## 3. Lifecycles, rights and operational response

**Sandbox hackathon:** keep only fictional data. At the end of judging (while preserving any materials needed by contest rules), stop the app, review any backups/screenshots, delete the local demo SQLite database and temporary materials, and rotate test credentials if exposed. No automated cleanup is currently implemented.

**If real personal data was entered accidentally:** disable `STEWARD_SANDBOX_LLM` and `STEWARD_SANDBOX_WRITES`, stop external calls, identify affected subjects, records and recipients, and consult the operator/controller's lawful retention and incident policy before any deletion. Do not delete records that must be retained for a legitimate legal obligation or dispute. Coordinate corrections and removal with PayPal and the model provider as appropriate; **this application currently has no end-to-end automated right-of-access, rectification, erasure, objection or export workflow**.

**Production deployment is out of scope.** Before using real invoices, a responsible organization must document its processing purpose and appropriate GDPR Article 6 legal basis, actual controller/processor roles, information notices (Articles 13/14 as applicable), vendor DPA under Article 28 where required, cross-border transfer mechanism, security measures, retention schedule, rights workflows, and incident response. The operator's opt-in alone satisfies none of these requirements.

## 4. Financial decisions and automated profiling

Forecasts are estimates from invoice history and can be inaccurate, especially after partial payments, delays and refunds. This MVP does **not** automatically deny credit, impose legal collection actions, block services, or change the customer's financial status. Human review is required for outbound communications. GDPR Article 22 requires a separate assessment **if** a future use constitutes a solely automated decision with legal or similarly significant effects; it is not a universal prohibition of all risk rankings. Disputes and customer rights require real human procedures in any actual deployment.

## 5. Outstanding gate evidence

- [ ] Test with synthetic PayPal sandbox Business account and an intentionally controlled model; record whether data is shared as documented.
- [ ] Verify the actual recipient/model provider terms and processing agreement **before** any live customer data is used.
- [ ] Implement retention/export/deletion controls and incident owner before a production deployment.
- [ ] Assess lawful basis, controller/processor roles and Article 22 applicability for the selected merchant and jurisdiction.
- [ ] Verify operator UI/browser screenshots and submission video do not include personal data or credentials.
- [ ] Keep #74 **open** until legal and data-rights acceptance criteria are truly met.

**Primary law (A):** [GDPR Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj), especially Articles 5, 6, 13–22, 25, 28 and 32; [European Commission on individual automated decision-making](https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en). **Technical guidance (B):** [EDPB AI and data protection](https://www.edpb.europa.eu/topics/ai-and-technology/artificial-intelligence_en), [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/).
