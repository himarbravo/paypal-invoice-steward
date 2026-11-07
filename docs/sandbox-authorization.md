# Single-merchant PayPal sandbox authorization boundary

**Status:** MVP technical contract, not merchant-identity verification or production authorization certification. Related: #73, #97, #69, #74, hackathon gate #83.

## Supported integration

Only the hackathon operator's **own single sandbox business merchant** and its app credentials. The app uses `client_credentials` against the canonical sandbox OAuth endpoint. Partner onboarding, third-party consent, live payments, multiple merchants and tenant isolation are **out of scope**.

An access token must contain the **exact** space-delimited permission `https://uri.paypal.com/services/invoicing`, a Bearer `token_type`, a non-empty token, finite positive `expires_in`, and a non-empty `app_id`. On failure, the client refuses to call the invoicing API; there is no silent fallback to simulated data. An optional `PAYPAL_APP_ID` environment variable pins the expected application ID.

**Critical distinction:** an OAuth `app_id` attests which PayPal API application supplied the token; **it does not establish ownership of a specific merchant account**. The PayPal token sample does not establish separate read vs. write invoicing scopes; only the single invoicing permission is checked. The application itself adds separate `STEWARD_SANDBOX_WRITES=enabled` approval gating.

## Operator procedure before demo

1. Open the PayPal Developer Dashboard, inspect **Sandbox → Apps & Credentials** for the intended app, and confirm that the sandbox **Business** account belongs to the operator. Record the account-to-app association privately, not in screenshots, code or logs.
2. Set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` and optionally `PAYPAL_APP_ID` in a local uncommitted `.env`. Start read-only. Never copy an OAuth token, client secret or personal customer invoice into documentation, video or AI prompt.
3. Verify read-only invoice listing in PayPal sandbox. In case of HTTP 401/403, scope mismatch, app mismatch or disconnected credentials, **stop**; do not use the offline demo as counterfeit sandbox proof.
4. Set a non-secret, local `STEWARD_OPERATOR_ID` (3–64 letters, numbers, dots, underscores or hyphens) and enable `STEWARD_SANDBOX_WRITES=enabled` only for an explicit supervised sandbox send, with synthetic recipient data and exact proposal approval. The server records this configured label with the approval event before the provider write. It is local process attribution, **not** login, identity proof, authorization, RBAC or tenant isolation. Turn writes off when the experiment ends and restart the app.
5. For credential rotation or revocation, rotate the secret in the PayPal dashboard, replace the local environment values, **restart the process** (clears any cached token) and verify behavior. This MVP has no centralized credential or account lifecycle manager.
6. No tenant boundary can be inferred from this app's local credentials: all invoice IDs must be considered scoped only to the **one configured merchant**. Cross-merchant onboarding is forbidden until a separate authorization architecture exists.

## Error and retry policy

- Missing invoicing scope, wrong app ID, invalid token type/expiry: **fail closed before any invoice request**.
- A GET returning 401 may refresh its token once; no **automatic retry of POST**, including invoice creation, send, reminder or search calls.
- A 403 is an authorization failure, never "no invoices".
- Uncertain outcomes for sending/creating are controlled by the existing proposal-state and manual reconciliation process (#60), which is not fully verified here.

## Verification and outstanding evidence

MockTransport tests establish deterministic scope and app-pinning behavior; they do **not** establish merchant ownership or real PayPal scopes granted to the operator's app. Record an actual sandbox test separately in issue #73 before concluding the access contract is validated.

**Source A:** [PayPal REST OAuth authentication](https://developer.paypal.com/api/rest/authentication), updated June 30, 2026; [PayPal Invoicing v2](https://developer.paypal.com/api/invoicing/v2/). **Source B:** [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/). App ID pinning and replay restrictions are project policies.
