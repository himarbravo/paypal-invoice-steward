# Project contract

Goal: help one merchant review receivables and approve invoice and reminder actions locally using PayPal Sandbox.

- J1: Configure → read invoices → propose → approve → verify → audit.
- I1: The model reads and proposes. The operator approves the exact outbound action.
- I2: Uncertain results remain explicit. Recovery must avoid duplicate external writes.
- I3: Financial output reflects verified source data and its limitations.
- I4: Sandbox writes and external AI are explicit opt-ins. Keep credentials and real customer data out of evidence.
- Release evidence: #83, #84, #101 and #140. Distinguish offline tests from provider evidence.

Critical changes include financial logic, external writes, security, migrations and safeguards including CI. Use a non-closing issue reference when verification must happen after merge.

## Independent criterion review

For critical changes, the orchestrator must appoint a separate criterion reviewer (a subagent in a fresh context, or a qualified human). Before implementation, give the reviewer the issue, project contract, current behavior and primary sources. Withhold the proposed solution. The reviewer records their identity or session, observable expected results, negative cases and required evidence in a dated comment on the issue. Implementation waits for this record. Changes to the criteria require another independent review and a linked rationale.

After implementation, the reviewer checks the diff and evidence against the agreed criteria and records a verdict and full head SHA in a GitHub comment. A new head requires a renewed review. The merge owner checks authorship, timing, verdict and SHA and resolves any policy or scope disagreement with the project owner. The workflow checks reference format and SHA equality. It cannot establish independence or evidence quality.
