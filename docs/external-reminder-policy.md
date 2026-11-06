# External reminder and notification boundary

Single-merchant sandbox scope; #72 remains open. This application records its own proposal/confirmation history and operator-managed local contact holds. It does not read merchant auto-reminder configuration, reconcile manual contact or suspend provider reminders.

## Provider contract checked 2026-11-06

The official [reminder API](https://developer.paypal.com/api/invoicing/v2/invoices-remind/) documents provider-generated subject/note and inherited invoice CC recipients when `additional_recipients` is omitted. Our request omits ignored custom text and explicitly supplies an empty additional-recipient list. The approval card describes provider-generated content; custom sandbox notes are refused. Actual recipient delivery must be checked with synthetic sandbox recipients in #101.

The [send API](https://developer.paypal.com/api/invoicing/v2/invoices-send/) schedules future-dated invoices. Scheduled read-backs are not marked sent; scheduled and payment-pending invoices cannot receive local reminders. Existing provider schedules may still execute independently.

The [Invoicing API inventory](https://developer.paypal.com/api/invoicing/v2/) exposes merchant reminder configuration retrieval, setup, update, suspend/resume, and invoice-level reminder cancellation. None are implemented here. Documentation of an endpoint is not proof of this merchant's permissions. No AI tool can change these settings.

## Operator preflight and conflict policy

1. Inspect PayPal's current invoice and automatic reminder settings, and the operator's known contact history.
2. If a dispute, complaint, contact preference or other review conflicts with sending, use **Hold local reminders** on that invoice, choose the reason and resolve with the account owner. Local holds block new reminder proposals and confirmation of already queued ones. Release only after investigation, using the explicit **Release local hold** action. No model tool can set or release a hold.
3. Manage external schedules directly in PayPal when appropriate and confirm the provider result. Never represent a local dismissal/cooldown as stopping PayPal sends.
4. Approve only after reviewing the recipient, remaining balance and provider-content notice. Local status revalidation still runs before the request.

The three-day cooldown is local product policy. PayPal's documented two-reminders-per-day API limit is not a complete cross-channel contact policy or a legal contact-frequency rule. Unknown external settings remain unknown in the UI. Dependencies: #43 contact cadence, #46 dispute handling, #49 escalation, #65 reminder generation, #70 approval/audit.

Holds and set/release audit events persist in the single-merchant SQLite database. Release compares the exact hold version shown to the operator, so a stale browser cannot clear a later hold. Confirmation checks holds inside its atomic execution reservation and again immediately before sending. A local hold **cannot recall an in-flight request** or guarantee there is no change between the final check and PayPal's POST. External reminders remain unverified until the operator checks PayPal. The localhost operator is the case owner; there is no authenticated multi-user assignment, provider dispute case or automatic adjudication. `GET /api/invoices/{id}/hold` provides the local hold audit history.
