# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/). See [docs/versioning.md](docs/versioning.md).

## [Unreleased]

### Added

- Project skeleton: `paypal_invoice_steward` package, tests, documentation, working protocol and CI.
- Web app (`paypal-invoice-steward`): chat assistant, cash-flow forecast for the next 8 weeks, and invoice and reminder proposals that a person confirms before anything is sent.
- PayPal sandbox and offline demo backends; Claude assistant when `ANTHROPIC_API_KEY` is set, rule-based assistant otherwise.
- Safe execution: what is sent is exactly what was reviewed, a double confirmation sends once, and a lost PayPal response is marked unverified and checked before any retry.

[Unreleased]: https://github.com/himarbravo/paypal-invoice-steward/commits/main
