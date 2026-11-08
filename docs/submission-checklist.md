# Hackathon submission checklist

Use this checklist for the final submission only. It is a delivery aid, not proof of
production readiness, legal compliance, merchant ownership or accounting reconciliation.

**Official requirements:** [PayPal AI Hackathon rules](https://paypalaihackathon.devpost.com/rules)
and [challenge page](https://paypalaihackathon.devpost.com/). The project needs a
meaningful PayPal Sandbox integration and an AI tool, a functional demo judges can run
or interact with, a public open-source repository, a public YouTube demonstration under
three minutes, and a complete submission description.

## Repository and reproducibility

- [ ] `main` is clean and the final GitHub Actions checks are green.
- [ ] A fresh local clone installs and starts with the README instructions, without
  copying any credentials into the repository.
- [ ] `./scripts/check.sh` passes on a supported Python version.
- [x] The repository includes the visible [MIT license](../LICENSE) and a public setup
  guide in [README.md](../README.md).
- [ ] `.env`, local SQLite data, screenshots with private data and generated recordings
  are not staged or committed.
- [ ] README commands, `.env.example` and actual configuration names agree.

## Functional evidence

- [x] The current evidence record shows real PayPal Sandbox list/show/search behavior,
  a real Claude-enabled pending proposal and separately authorized Sandbox action
  read-back. See [#101](https://github.com/himarbravo/paypal-invoice-steward/issues/101).
- [ ] Recording data is fictional and belongs only to the configured Sandbox merchant.
- [ ] The recording shows a live read plus a Claude proposal, not a static mockup.
- [ ] Any offline failure fixture is visibly labelled **offline simulation**.
- [ ] A new Sandbox write is performed only under a separate explicit operator
  authorization; it is not necessary for the normal recording path.

## Security and privacy review

- [ ] Video, screenshots, Devpost text and repository diff contain no secret, access
  token, personal email, real customer record or private invoice identifier.
- [ ] The demo remains localhost-only; it is not exposed through a public tunnel or an
  unauthenticated hosted URL.
- [ ] `STEWARD_SANDBOX_WRITES=disabled` is restored after any explicit Sandbox-write
  verification.
- [ ] `STEWARD_SANDBOX_LLM=disabled` is restored after recording unless another
  intentional, synthetic-data AI demonstration is immediately pending.
- [ ] Claims remain bounded: one Sandbox merchant/app, app-visible inventory, no
  merchant-wide ledger, no autonomous money movement, no production readiness claim.

## Devpost submission

- [ ] Project title and one-sentence value proposition are clear to a non-specialist.
- [ ] Description identifies **PayPal Invoicing v2 Sandbox** and **Claude** and explains
  the meaningful role of each.
- [ ] Description explains the human approval boundary and the real user problem.
- [ ] Public repository URL is added; it contains source, license and complete setup.
- [ ] Public YouTube URL is added; the video is below three minutes and shows the app
  functioning.
- [ ] Tool/model disclosure and any team/member details are complete and accurate.

## Final decision

Do not submit until the unchecked items required for the selected judge path are
evidenced. Prefer a reproducible local setup over an unsafe public deployment. The
rules allow judges to run the application from clear repository instructions; a static
mockup is not enough.
