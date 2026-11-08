# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/). See [docs/versioning.md](docs/versioning.md).

## [Unreleased]

### Fixed

- Reject Sandbox financial inventory and reminder preparation/preflight when one PayPal payment receipt ID is reported on more than one invoice; keep receipt IDs out of public product data (#151).
- Reject a read-only verification observation if a concurrent confirmation has already completed the proposal, keeping the audit order coherent (#149).
- Commit each proposal state transition with its matching audit event, including the pre-write confirmation attribution, so a local persistence failure cannot leave one without the other (#147).
- Constrain the Anthropic SDK to the tested 1.x series while the 2.x import stalls on local Python 3.14 (#135).
- Require a configured local operator audit label for sandbox writes and record it with the approval event; this is not authentication or role authorization (#137).
- Allow a read-only exact-match recovery check for interrupted invoice executions while keeping sends/retries blocked (#134).
- Atomically reuse equivalent active invoice proposals across local SQLite connections, preventing concurrent requests from receiving separate PayPal references (#132).
- Accept PayPal Sandbox's zero-total invoice list when it omits the `items` key, while retaining fail-closed validation for every other malformed list shape (#130).
- Load local configuration only from the application's working directory so developer credentials do not leak into isolated tests (#128).
- Verify the provider's ordered line items and note against the approved invoice before sending or reporting recovery as complete (#126).
- Atomically reserve reminder sends per invoice, enforce cooldown at confirmation across processes/restarts, and reject changed proposal snapshots (#120).
- Reject missing/invalid provider invoice dates, face amounts and currencies instead of fabricating financial source facts (#118).
- Disclose PayPal-generated reminder content and external contact limits, request no inherited CC, and block reminders for scheduled/pending-payment invoices (#116).
- Validate approved invoice read-back fields before send/verification and require confirmed sent/paid state before reporting completion (#114).
- Reject nonfinite invoice values and recompute stored-payload approval hashes before execution; revalidate legacy invoice policy (#112).
- Block invoice retries on incomplete or ambiguous reference searches and reread matched invoices before use (#110).
- Reject unsafe invoice path identifiers and mismatched PayPal read-back identities (#108).
- Quarantine PayPal refund statuses instead of marking them cancelled; fail closed on unresolved refund totals and revalidate each queued reminder before sending (#106).
- Separate PayPal invoice face from verified outstanding due_amount, avoid fabricated paid dates, preserve reported payment origin and block financial advice/reminders on missing balances (#104).
- Reject incomplete or inconsistent PayPal invoice pagination instead of silently truncating after 20 pages; block downstream financial outputs and clear stale browser figures (#102).
- Require an explicit sandbox opt-in before sending operator chat to an external LLM; document real data flows, lifecycle gaps and policy limitations (#99).
- Fail closed when the sandbox OAuth token lacks the invoicing scope, Bearer type, app ID or valid lifetime; optionally pin an expected app ID and avoid automatic POST replay after 401 (#97).
- Minimize PayPal-derived tool output to opaque identifiers and financial fields before sending data to the LLM; omit free-text customer and proposal details and add adversarial tests (#95).
- Redact upstream PayPal error text before it reaches browser responses, agent tools, proposal/audit records or agent error logs (#93).
- Default sandbox operations to read-only; require an explicit environment opt-in before approved invoice and reminder sends, with an HTTP 403 and audit entry when blocked (#91).
- Reject untrusted sandbox-lookalike endpoints, partial PayPal credentials and unsupported modes instead of silently falling back to demo mode (#73).
- Reject non-loopback HTTP clients, forged Host headers, cross-origin browser writes and non-loopback bind addresses in the unauthenticated hackathon demo (#85).

### Added

- Add durable operator-managed contact holds, block queued/new reminders, audit set/release and prevent stale release of a newer hold (#124).
- Persist app-scoped invoice-read timestamps and missing-record exceptions; show freshness in the browser and block totals when previously observed IDs disappear (#122).
- Project skeleton: `paypal_invoice_steward` package, tests, documentation, working protocol and CI.
- Web app (`paypal-invoice-steward`): chat assistant, cash-flow forecast for the next 8 weeks, and invoice and reminder proposals that a person confirms before anything is sent.
- PayPal sandbox and offline demo backends; Claude assistant when `ANTHROPIC_API_KEY` is set, rule-based assistant otherwise.
- Safe execution: what is sent is exactly what was reviewed, a double confirmation sends once, and a lost PayPal response is marked unverified and checked before any retry.

[Unreleased]: https://github.com/himarbravo/paypal-invoice-steward/commits/main
